"use client";

import { useEffect, useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import services from "../../services/service";
import { useCart } from "../../contexts/CartContext";
import {
  Inventory2Outlined,
  Search,
  FilterList,
  ExpandMore,
  ExpandLess,
  StorefrontOutlined,
  EmojiEventsOutlined,
  AccessTimeOutlined,
  FilterAltOutlined,
  MapOutlined,
  WarningAmberRounded,
  CloudUploadOutlined,
  AddShoppingCart,
  StyleOutlined,
  LocalOfferOutlined,
} from "@mui/icons-material";

/* =======================
   CONFIGURAÇÃO DE DESCONTOS
======================= */
const REGRAS_DESCONTO: Record<string, number> = {
  "portalcomdip": 0.04, // 4%
  "g&b": 0.07,          // 7%
  "g & b": 0.07,        // Caso venha com espaços
};

/* =======================
   TIPOS
======================= */
type Regiao = {
  uf: string;
  preco: number;
  preco_formatado: string;
  estoque: number;
  preco_original?: number;
};

type Oferta = {
  fornecedor: string;
  preco: number;
  preco_formatado: string;
  estoque: number;
  data_atualizacao: string;
  preco_original?: number;
  teve_desconto?: boolean;
  percentual_desconto_aplicado?: number; // ✅ Novo campo para mostrar na badge
  regioes?: Regiao[];
};

type ProdutoComparado = {
  codigo: string;
  nome: string;
  imagem: string | null;
  marca?: string | null;
  fornecedor_vencedor: string;
  melhor_preco: number;
  melhor_preco_formatado: string;
  ofertas?: Oferta[];
  item_pai?: ProdutoComparado | null;
  tem_item_pai?: boolean;
  variacoes?: ProdutoComparado[];
};

type RetornoComparar = {
  success: boolean;
  total_produtos_analisados?: number;
  ultima_data_processamento?: string;
  ultima_data_processamento_iso?: string;
  comparativo?: ProdutoComparado[];
  data?: {
    ultima_data_processamento?: string;
    ultima_data_processamento_iso?: string;
    comparativo?: ProdutoComparado[];
  };
};

/* =======================
   HELPERS
======================= */
function formatBRL(value: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value || 0);
}

function formatPercent(valueDecimal: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "percent",
    minimumFractionDigits: 0, // Ex: 4%
    maximumFractionDigits: 1, // Ex: 4.5%
  }).format(valueDecimal || 0);
}

// Helper para formatar porcentagem mais técnica (impostos)
function formatPercentTecnico(valueDecimal: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(valueDecimal || 0);
}

/* =======================
   TRIBUTOS ES
======================= */
const AGREGADO_MVA_ES = 0.8896;

function approxEqual(a: number, b: number, tolerance = 0.00005) {
  return Math.abs(a - b) <= tolerance;
}

function calcSes(agregadoMvaDecimal: number, custoES: number) {
  if (approxEqual(agregadoMvaDecimal, 1.0614)) return custoES * 0.04;
  if (approxEqual(agregadoMvaDecimal, 0.8896)) return custoES * 0.12;
  if (approxEqual(agregadoMvaDecimal, 0)) return 0;
  return 0;
}

function calcTributosES(custoES: number) {
  const mva = custoES * AGREGADO_MVA_ES;
  const bcIcmsSt = custoES + mva;
  const ses = calcSes(AGREGADO_MVA_ES, custoES);
  const icmsStMaisFcp = bcIcmsSt * 0.18 + bcIcmsSt * 0.02 - ses;
  const custoMercadoria = custoES + icmsStMaisFcp;

  return {
    agregadoMva: AGREGADO_MVA_ES,
    mva,
    bcIcmsSt,
    icmsStMaisFcp,
    custoMercadoria,
  };
}

/* =======================
   SUB-COMPONENTE: CARD DE OFERTA
======================= */
const OfertaCard = ({
  oferta,
  produtoAlvo,
  selectedSupplier,
  regiaoSelecionada,
  setRegiaoSelecionada,
  addToCart,
}: {
  oferta: Oferta;
  produtoAlvo: ProdutoComparado;
  selectedSupplier: string;
  regiaoSelecionada: Record<string, string>;
  setRegiaoSelecionada: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  addToCart: (item: any) => void;
}) => {
  const [quantidade, setQuantidade] = useState<number>(1);

  const isWinner = oferta.fornecedor === produtoAlvo.fornecedor_vencedor;
  const isSelectedSupplier = selectedSupplier === oferta.fornecedor;
  const keyOferta = `${produtoAlvo.codigo}-${oferta.fornecedor}`;

  const ufEscolhida = regiaoSelecionada[keyOferta];
  const precisaSelecionarUF = (oferta.regioes?.length || 0) > 1 && !ufEscolhida;

  const ufAtual =
    regiaoSelecionada[keyOferta] ||
    (oferta.regioes?.length === 1 ? oferta.regioes?.[0]?.uf : "") ||
    "";

  const regSelecionada = oferta.regioes?.find((r) => r.uf === ufAtual);
  const precoOriginalDinamico = (regSelecionada?.preco_original ?? oferta.preco_original) || 0;
  const deveMostrarOriginal =
    !!(regSelecionada?.preco_original || oferta.preco_original) && precoOriginalDinamico > 0;

  const regES = oferta.regioes?.find((r) => (r.uf || "").toUpperCase() === "ES");
  const calcES = regES ? calcTributosES(regES.preco) : null;

  const handleAddToCart = (e: React.MouseEvent) => {
    e.stopPropagation();
    const ufFinal =
      regiaoSelecionada[keyOferta] ||
      (oferta.regioes?.length === 1 ? oferta.regioes?.[0]?.uf : "") ||
      "";

    const regObj = oferta.regioes?.find((r) => r.uf === ufFinal);
    const precoFinal = regObj?.preco ?? oferta.preco;
    const precoOriginalFinal = regObj?.preco_original ?? oferta.preco_original;

    addToCart({
      uid: `${produtoAlvo.codigo}-${oferta.fornecedor}-${ufFinal || "GERAL"}`,
      codigo: produtoAlvo.codigo,
      nome: produtoAlvo.nome,
      imagem: produtoAlvo.imagem || "",
      marca: produtoAlvo.marca || "",
      fornecedor: oferta.fornecedor,
      preco: precoFinal,
      quantidade: Number(quantidade),
      uf: ufFinal || undefined,
      origem: regObj ? "REGIAO" : "OFERTA_GERAL",
      teve_desconto: !!(regObj?.preco_original || oferta.preco_original),
      preco_original: precoOriginalFinal,
    });
  };

  return (
    <div
      className={`relative p-4 rounded-xl border bg-white flex flex-col justify-between transition-colors
        ${
          isWinner
            ? "border-emerald-500 ring-1 ring-emerald-500 shadow-emerald-100 shadow-lg"
            : isSelectedSupplier
            ? "border-indigo-400 ring-1 ring-indigo-200"
            : "border-gray-200 hover:border-gray-300"
        }
      `}
    >
      {isWinner && (
        <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-500 text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wide flex items-center gap-1 shadow-sm z-10">
          <EmojiEventsOutlined style={{ fontSize: 14 }} /> Melhor Preço
        </div>
      )}

      <div>
        <div
          className={`font-semibold text-sm mb-1 truncate ${
            isWinner ? "text-emerald-700" : "text-gray-800"
          }`}
          title={oferta.fornecedor}
        >
          {oferta.fornecedor}
        </div>
        <div className="text-xs text-gray-400 flex items-center gap-1 mb-2">
          <AccessTimeOutlined style={{ fontSize: 12 }} /> {oferta.data_atualizacao}
        </div>
      </div>

      {/* REGIÕES */}
      {oferta.regioes && oferta.regioes.length > 0 && (
        <div className="mb-3 mt-2 bg-gray-50 rounded p-2 border border-gray-100">
          <div className="flex items-center gap-1 text-[10px] font-bold text-gray-500 uppercase mb-1.5">
            <MapOutlined style={{ fontSize: 12 }} /> Preço por Região
          </div>
          <div className="space-y-1">
            {oferta.regioes.map((reg) => {
              const checked =
                ufEscolhida === reg.uf ||
                ((oferta.regioes?.length || 0) === 1 && (!ufEscolhida || ufEscolhida === ""));
              return (
                <label
                  key={reg.uf}
                  className="flex justify-between items-center text-xs cursor-pointer select-none"
                >
                  <div className="flex items-center gap-2">
                    <input
                      type="radio"
                      name={`reg-${keyOferta}`}
                      checked={checked}
                      onChange={() =>
                        setRegiaoSelecionada((prev) => ({ ...prev, [keyOferta]: reg.uf }))
                      }
                    />
                    <span className="font-medium text-gray-600 bg-gray-200 px-1 rounded text-[10px] min-w-[20px] text-center">
                      {reg.uf}
                    </span>
                  </div>
                  <div className="flex gap-2 items-center">
                    <span className="text-gray-400 text-[10px]">{reg.estoque} un</span>
                    <div className="text-right">
                      {reg.preco_original && (
                        <span className="block text-[8px] text-gray-400 line-through mr-1">
                          {formatBRL(reg.preco_original)}
                        </span>
                      )}
                      <span
                        className={`font-semibold ${
                          isWinner ? "text-emerald-700" : "text-gray-800"
                        }`}
                      >
                        {reg.preco_formatado}
                      </span>
                    </div>
                  </div>
                </label>
              );
            })}
          </div>

          {precisaSelecionarUF && (
            <p className="mt-2 text-[11px] text-amber-700 font-semibold">Selecione a UF.</p>
          )}

          {/* CÁLCULO ES */}
          {regES && calcES && (
            <div className="mt-3 bg-white border border-indigo-100 rounded-lg p-3">
              <div className="text-[10px] font-bold text-indigo-700 uppercase tracking-wide mb-2">
                ES — Cálculo Tributário
              </div>
              <div className="grid grid-cols-2 gap-2 text-[12px]">
                <div className="bg-gray-50 rounded p-2 border border-gray-100">
                  <div className="text-[10px] text-gray-500 font-bold uppercase">(AGREGADO) MVA</div>
                  <div className="font-semibold text-gray-800">
                    {formatPercentTecnico(calcES.agregadoMva)}
                  </div>
                </div>
                <div className="bg-gray-50 rounded p-2 border border-gray-100">
                  <div className="text-[10px] text-gray-500 font-bold uppercase">MVA (R$)</div>
                  <div className="font-semibold text-gray-800">{formatBRL(calcES.mva)}</div>
                </div>
                <div className="bg-gray-50 rounded p-2 border border-gray-100">
                  <div className="text-[10px] text-gray-500 font-bold uppercase">BC ICMS ST</div>
                  <div className="font-semibold text-gray-800">{formatBRL(calcES.bcIcmsSt)}</div>
                </div>
                <div className="bg-gray-50 rounded p-2 border border-gray-100">
                  <div className="text-[10px] text-gray-500 font-bold uppercase">ICMS ST + FCP</div>
                  <div className="font-semibold text-gray-800">
                    {formatBRL(calcES.icmsStMaisFcp)}
                  </div>
                </div>
                <div className="col-span-2 bg-indigo-50 rounded p-2 border border-indigo-100">
                  <div className="text-[10px] text-indigo-700 font-bold uppercase">
                    CUSTO MERCADORIA (ES)
                  </div>
                  <div className="text-lg font-extrabold text-indigo-700">
                    {formatBRL(calcES.custoMercadoria)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-auto pt-3 border-t border-gray-100">
        <div className="flex items-end justify-between mb-3">
          <div>
            <span className="block text-[10px] text-gray-500 uppercase">Estoque</span>
            <span
              className={`text-sm font-medium ${
                oferta.estoque > 0 ? "text-gray-700" : "text-red-400"
              }`}
            >
              {oferta.estoque} un
            </span>
          </div>
          <div className="text-right">
            {deveMostrarOriginal && (
              <div className="flex flex-col items-end mb-1">
                {oferta.teve_desconto && (
                  // ✅ Badge dinâmica: Mostra 4% OFF ou 7% OFF dependendo do fornecedor
                  <span className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded font-bold uppercase tracking-wide">
                    {formatPercent(oferta.percentual_desconto_aplicado || 0)} OFF
                  </span>
                )}
                <span className="text-xs text-gray-400 line-through decoration-gray-400">
                  {formatBRL(precoOriginalDinamico)}
                </span>
              </div>
            )}
            <span
              className={`text-lg font-bold ${isWinner ? "text-emerald-600" : "text-gray-700"}`}
            >
              {oferta.preco_formatado}
            </span>
          </div>
        </div>

        <div className="flex gap-2">
           <input 
              type="number"
              min="1"
              value={quantidade}
              onClick={(e) => e.stopPropagation()}
              onChange={(e) => setQuantidade(Number(e.target.value))}
              className="w-16 border border-gray-300 rounded-lg px-2 text-center text-sm font-semibold focus:ring-2 focus:ring-indigo-500 outline-none"
           />
           
            <button
            disabled={precisaSelecionarUF}
            onClick={handleAddToCart}
            className={`flex-1 py-2 px-3 rounded-lg flex items-center justify-center gap-2 text-sm font-bold transition-all
                ${
                precisaSelecionarUF
                    ? "bg-gray-200 text-gray-500 cursor-not-allowed"
                    : isWinner
                    ? "bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-200 shadow-md"
                    : "bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-100"
                }
            `}
            >
            <AddShoppingCart fontSize="small" /> Add
            </button>
        </div>
      </div>
    </div>
  );
};

/* =======================
   PÁGINA PRINCIPAL
======================= */
export default function ComparativoPrecosPage() {
  const router = useRouter();
  const { addToCart } = useCart();

  const [produtos, setProdutos] = useState<ProdutoComparado[]>([]);
  const [loading, setLoading] = useState(true);
  const [dataLote, setDataLote] = useState<string>("");
  const [dadosDesatualizados, setDadosDesatualizados] = useState(false);

  const [search, setSearch] = useState("");
  const [selectedSupplier, setSelectedSupplier] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  const [regiaoSelecionada, setRegiaoSelecionada] = useState<Record<string, string>>({});

  /* =======================
     PROCESSAMENTO DE DESCONTOS MULTI-FORNECEDOR
  ======================= */
  const processarOfertasDoProduto = (prod: ProdutoComparado): ProdutoComparado => {
    if (!prod.ofertas || prod.ofertas.length === 0) return prod;

    const ofertasAtualizadas = prod.ofertas.map((oferta) => {
      const fornecedorKey = oferta.fornecedor.toLowerCase().trim();
      
      // ✅ Busca a taxa no objeto de configuração (0.04 ou 0.07)
      const taxaDesconto = REGRAS_DESCONTO[fornecedorKey];

      if (taxaDesconto) {
        const precoOriginal = oferta.preco;
        // Aplica o desconto: Preço * (1 - 0.04) ou Preço * (1 - 0.07)
        const novoPreco = precoOriginal * (1 - taxaDesconto);

        const regioesAtualizadas = oferta.regioes?.map((reg) => {
          const precoRegOriginal = reg.preco;
          const novoPrecoReg = precoRegOriginal * (1 - taxaDesconto);
          return {
            ...reg,
            preco: novoPrecoReg,
            preco_original: precoRegOriginal,
            preco_formatado: formatBRL(novoPrecoReg),
          };
        });

        return {
          ...oferta,
          preco: novoPreco,
          preco_formatado: formatBRL(novoPreco),
          preco_original: precoOriginal,
          teve_desconto: true,
          percentual_desconto_aplicado: taxaDesconto, // Salva para exibir na badge
          regioes: regioesAtualizadas,
        };
      }

      return oferta;
    });

    const ofertasOrdenadas = [...ofertasAtualizadas].sort((a, b) => a.preco - b.preco);
    const melhorOferta = ofertasOrdenadas[0];

    return {
      ...prod,
      ofertas: ofertasAtualizadas,
      fornecedor_vencedor: melhorOferta ? melhorOferta.fornecedor : prod.fornecedor_vencedor,
      melhor_preco: melhorOferta ? melhorOferta.preco : prod.melhor_preco,
      melhor_preco_formatado: melhorOferta ? melhorOferta.preco_formatado : prod.melhor_preco_formatado,
    };
  };

  const processarEstruturaCompleta = (lista: ProdutoComparado[]) => {
    return lista.map((item) => {
      let itemPaiProcessado = item.item_pai ? processarOfertasDoProduto(item.item_pai) : undefined;
      let itemRaizProcessado = processarOfertasDoProduto(item);
      let variacoesProcessadas: ProdutoComparado[] = [];
      if (item.variacoes && item.variacoes.length > 0) {
        variacoesProcessadas = item.variacoes.map((v) => processarOfertasDoProduto(v));
      }
      return {
        ...itemRaizProcessado,
        item_pai: item.item_pai ? itemPaiProcessado : null,
        variacoes: variacoesProcessadas,
      };
    });
  };

  async function carregar() {
    setLoading(true);
    setDadosDesatualizados(false);
    try {
      const result: RetornoComparar = await services("/comparar", { method: "GET" });
      console.log("📦 Retorno da API:", result);
      let lista: ProdutoComparado[] = [];
      if (result?.comparativo) lista = result.comparativo;
      else if (result?.data?.comparativo) lista = result.data.comparativo;

      const ultimaData =
        result?.ultima_data_processamento || result?.data?.ultima_data_processamento || "";

      if (ultimaData) {
        verificarData(ultimaData);
      } else if (lista.length > 0) {
        const primeiraOferta =
          lista[0]?.ofertas?.[0]?.data_atualizacao ||
          lista[0]?.item_pai?.ofertas?.[0]?.data_atualizacao ||
          lista[0]?.variacoes?.[0]?.ofertas?.[0]?.data_atualizacao;
        if (primeiraOferta) verificarData(primeiraOferta);
      }

      if (lista.length > 0) {
        setProdutos(processarEstruturaCompleta(lista));
      } else {
        setProdutos([]);
      }
    } catch (error) {
      console.error("Erro crítico ao carregar:", error);
    } finally {
      setLoading(false);
    }
  }

  const verificarData = (dataString: string) => {
    if (!dataString) return;
    const somenteData = dataString.split(" ")[0];
    const [dia, mes, ano] = somenteData.split("/").map(Number);
    const dataArquivo = new Date(ano, mes - 1, dia);
    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);
    setDadosDesatualizados(dataArquivo < hoje);
    setDataLote(dataString);
  };

  useEffect(() => {
    carregar();
  }, []);

  const listaFornecedores = useMemo(() => {
    const fornecedoresSet = new Set<string>();
    const extrair = (ofertas?: Oferta[]) => {
      if (!ofertas) return;
      ofertas.forEach((o) => {
        if (o.fornecedor) fornecedoresSet.add(o.fornecedor);
      });
    };
    produtos.forEach((p) => {
      extrair(p.ofertas);
      if (p.item_pai) extrair(p.item_pai.ofertas);
      p.variacoes?.forEach((v) => extrair(v.ofertas));
    });
    return Array.from(fornecedoresSet).sort();
  }, [produtos]);

  const produtosFiltrados = produtos.filter((p) => {
    const termo = search.toLowerCase();
    const matchTextoPai =
      (p.codigo?.toLowerCase() || "").includes(termo) ||
      (p.nome?.toLowerCase() || "").includes(termo) ||
      (p.fornecedor_vencedor?.toLowerCase() || "").includes(termo);
    const matchTextoVariacao = p.variacoes?.some(
      (v) =>
        (v.codigo?.toLowerCase() || "").includes(termo) ||
        (v.nome?.toLowerCase() || "").includes(termo)
    );
    const matchFornecedor =
      selectedSupplier === "" ||
      p.ofertas?.some((o) => o.fornecedor === selectedSupplier) ||
      (p.item_pai && p.item_pai.ofertas?.some((o) => o.fornecedor === selectedSupplier)) ||
      (p.variacoes &&
        p.variacoes.some((v) => v.ofertas?.some((o) => o.fornecedor === selectedSupplier)));

    return (matchTextoPai || matchTextoVariacao) && matchFornecedor;
  });

  const totalProdutos = produtos.length;
  const totalOfertas = produtos.reduce((acc, p) => {
    let count = p.ofertas?.length || 0;
    if (p.item_pai) count += p.item_pai.ofertas?.length || 0;
    if (p.variacoes) count += p.variacoes.reduce((vac, v) => vac + (v.ofertas?.length || 0), 0);
    return acc + count;
  }, 0);

  const RenderListaOfertas = ({ produtoAlvo }: { produtoAlvo: ProdutoComparado }) => {
    if (!produtoAlvo.ofertas || produtoAlvo.ofertas.length === 0) {
      return <p className="text-gray-400 text-sm italic py-2">Nenhuma oferta direta disponível.</p>;
    }

    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {produtoAlvo.ofertas.map((oferta, idx) => (
          <OfertaCard
            key={`${produtoAlvo.codigo}-${oferta.fornecedor}-${idx}`}
            oferta={oferta}
            produtoAlvo={produtoAlvo}
            selectedSupplier={selectedSupplier}
            regiaoSelecionada={regiaoSelecionada}
            setRegiaoSelecionada={setRegiaoSelecionada}
            addToCart={addToCart}
          />
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="flex flex-col items-center animate-pulse">
          <div className="h-12 w-12 bg-indigo-200 rounded-full mb-4"></div>
          <p className="text-gray-500 font-medium">Carregando comparativo...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6 md:p-10 font-sans text-gray-800">
      <div className="max-w-7xl mx-auto space-y-6">
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Comparativo de Preços</h1>
            <p className="text-gray-500 mt-1">
              Análise em tempo real.{" "}
              {dataLote && (
                <span className="ml-2 bg-gray-100 px-2 py-0.5 rounded text-xs text-gray-600 font-medium border border-gray-200">
                  Dados de: {dataLote}
                </span>
              )}
            </p>
          </div>
          <button
            onClick={carregar}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg shadow-sm transition-all active:scale-95 flex items-center gap-2"
          >
            🔄 Atualizar Dados
          </button>
        </header>

        {dadosDesatualizados && (
          <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <WarningAmberRounded className="text-amber-600 mt-0.5" />
              <div>
                <h3 className="font-bold text-amber-800">Atenção: Dados Desatualizados</h3>
                <p className="text-sm text-amber-700 mt-1">
                  Os dados exibidos são do dia <strong>{dataLote}</strong>.
                </p>
              </div>
            </div>
            <button
              onClick={() => router.push("/upload")}
              className="whitespace-nowrap px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-bold rounded shadow-sm flex items-center gap-2"
            >
              <CloudUploadOutlined fontSize="small" /> Fazer Upload Novo
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <KpiCard
            titulo="Produtos Listados"
            valor={totalProdutos}
            icon={<Inventory2Outlined className="text-indigo-600" />}
            bg="bg-indigo-50"
          />
          <KpiCard
            titulo="Total de Ofertas (incl. variações)"
            valor={totalOfertas}
            icon={<StorefrontOutlined className="text-emerald-600" />}
            bg="bg-emerald-50"
          />
        </div>

        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col md:flex-row gap-4 items-center">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-xl" />
            <input
              type="text"
              placeholder="Pesquisar por código, nome..."
              className="w-full pl-10 pr-4 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none transition text-sm"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div className="relative w-full md:w-64">
            <div className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
              <FilterAltOutlined className="text-gray-400 text-xl" />
            </div>
            <select
              value={selectedSupplier}
              onChange={(e) => setSelectedSupplier(e.target.value)}
              className="w-full pl-10 pr-8 py-3 bg-gray-50 border border-gray-200 rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none appearance-none text-sm text-gray-700 cursor-pointer"
            >
              <option value="">Todos os Fornecedores</option>
              {listaFornecedores.map((f) => (
                <option key={f} value={f}>
                  {f}
                </option>
              ))}
            </select>
            <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
              <ExpandMore className="text-gray-400" fontSize="small" />
            </div>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500 whitespace-nowrap px-2 border-l border-gray-100 pl-4">
            <FilterList className="text-gray-400" /> <span>{produtosFiltrados.length} itens</span>
          </div>
        </div>

        <div className="space-y-4">
          {produtosFiltrados.map((produto) => {
            const isExpanded = expanded === produto.codigo;
            const displayItem = produto.item_pai || produto;
            const qtdVariacoes = produto.variacoes?.length || 0;
            const temOfertasPrincipal = displayItem.ofertas && displayItem.ofertas.length > 0;

            return (
              <div
                key={produto.codigo}
                className={`bg-white rounded-xl border transition-all duration-300 overflow-hidden ${
                  isExpanded
                    ? "border-indigo-200 shadow-md ring-1 ring-indigo-50"
                    : "border-gray-200 shadow-sm hover:border-gray-300"
                }`}
              >
                {/* HEADER DO CARD */}
                <div
                  className="p-5 flex flex-col md:flex-row items-center gap-6 cursor-pointer"
                  onClick={() => setExpanded(isExpanded ? null : produto.codigo)}
                >
                  <div className="flex-shrink-0 w-16 h-16 md:w-20 md:h-20 bg-gray-100 rounded-lg border border-gray-100 p-2 flex items-center justify-center relative">
                    <img
                      src={displayItem.imagem || "https://via.placeholder.com/150"}
                      alt={displayItem.nome}
                      className="w-full h-full object-contain mix-blend-multiply"
                      onError={(e) => (e.currentTarget.src = "https://via.placeholder.com/150")}
                    />
                    {qtdVariacoes > 0 && (
                      <div
                        className="absolute -bottom-2 -right-2 bg-indigo-600 text-white text-[10px] w-6 h-6 rounded-full flex items-center justify-center border-2 border-white shadow-sm"
                        title={`${qtdVariacoes} variações`}
                      >
                        +{qtdVariacoes}
                      </div>
                    )}
                  </div>

                  <div className="flex-1 text-center md:text-left overflow-hidden w-full">
                    <div className="flex flex-col md:flex-row md:items-center justify-center md:justify-start gap-2 mb-1">
                      <div className="flex items-center gap-2 justify-center md:justify-start">
                        <div className="text-xs font-bold text-gray-400 uppercase tracking-wider">
                          {produto.codigo}
                        </div>
                        {produto.tem_item_pai && (
                          <span className="text-[10px] bg-gray-100 text-gray-500 px-1.5 rounded">
                            Agrupador
                          </span>
                        )}
                      </div>
                      
                      {displayItem.marca && (
                        <div className="flex items-center gap-1 text-[10px] text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full font-semibold border border-indigo-100 w-fit mx-auto md:mx-0">
                           <LocalOfferOutlined style={{ fontSize: 12 }} /> {displayItem.marca}
                        </div>
                      )}
                    </div>

                    <h3 className="text-lg font-semibold text-gray-900 leading-tight truncate">
                      {displayItem.nome}
                    </h3>
                    <div className="mt-1 text-sm text-gray-500 flex items-center gap-2 justify-center md:justify-start">
                      <span>{(displayItem.ofertas || []).length} ofertas no principal</span>
                      {qtdVariacoes > 0 && (
                        <span className="text-indigo-600 bg-indigo-50 px-2 py-0.5 rounded-full text-xs font-medium">
                          + {qtdVariacoes} variações
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="text-center md:text-right min-w-[140px]">
                    <div className="text-xs text-gray-500 mb-1">Melhor Preço (Ref.)</div>
                    <div className="text-xl md:text-2xl font-bold text-emerald-600">
                      {displayItem.melhor_preco_formatado}
                    </div>
                    <div className="text-xs font-medium text-indigo-600 mt-1 truncate max-w-[150px] mx-auto md:ml-auto">
                      {displayItem.fornecedor_vencedor}
                    </div>
                  </div>

                  <div className="hidden md:block text-gray-400">
                    {isExpanded ? <ExpandLess /> : <ExpandMore />}
                  </div>
                </div>

                {/* CORPO EXPANDIDO */}
                <div
                  className={`border-t border-gray-100 bg-gray-50 transition-all duration-300 ease-in-out ${
                    isExpanded ? "max-h-[3000px] opacity-100" : "max-h-0 opacity-0 hidden"
                  }`}
                >
                  <div className="p-5 md:p-8 space-y-8">
                    {temOfertasPrincipal && (
                      <div>
                        <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                          <StorefrontOutlined fontSize="small" /> Ofertas do Item Principal (
                          {displayItem.codigo})
                        </h4>
                        <RenderListaOfertas produtoAlvo={displayItem} />
                      </div>
                    )}

                    {produto.variacoes && produto.variacoes.length > 0 && (
                      <div className={temOfertasPrincipal ? "pt-6 border-t border-gray-200" : ""}>
                        <h4 className="text-lg font-bold text-indigo-900 mb-6 flex items-center gap-2 bg-indigo-50 p-3 rounded-lg border border-indigo-100">
                          <StyleOutlined /> Variações / Itens Relacionados
                        </h4>
                        <div className="space-y-8">
                          {produto.variacoes.map((variacao) => (
                            <div
                              key={variacao.codigo}
                              className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm"
                            >
                              <div className="flex items-center gap-4 mb-4 border-b border-gray-100 pb-3">
                                <div className="w-12 h-12 bg-gray-100 rounded flex items-center justify-center flex-shrink-0">
                                  {variacao.imagem ? (
                                    <img
                                      src={variacao.imagem}
                                      className="w-full h-full object-contain mix-blend-multiply"
                                    />
                                  ) : (
                                    <span className="text-xs text-gray-400">Sem img</span>
                                  )}
                                </div>
                                <div className="flex-1">
                                  <div className="flex items-center gap-2 mb-0.5">
                                     <div className="text-xs font-bold text-gray-400">
                                        {variacao.codigo}
                                     </div>
                                     {variacao.marca && (
                                         <span className="text-[9px] text-gray-500 bg-gray-100 px-1.5 rounded border border-gray-200">
                                            {variacao.marca}
                                         </span>
                                     )}
                                  </div>
                                  <div className="font-semibold text-gray-800">{variacao.nome}</div>
                                </div>
                                <div className="text-right">
                                  <div className="text-[10px] text-gray-500">Melhor:</div>
                                  <div className="font-bold text-emerald-600">
                                    {variacao.melhor_preco_formatado}
                                  </div>
                                </div>
                              </div>
                              <RenderListaOfertas produtoAlvo={variacao} />
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function KpiCard({ titulo, valor, icon, bg }: any) {
  return (
    <div className="bg-white p-5 rounded-xl border border-gray-100 shadow-sm flex items-center gap-4 hover:shadow-md transition-shadow">
      <div className={`p-3 rounded-lg ${bg}`}>{icon}</div>
      <div>
        <p className="text-sm text-gray-500 font-medium">{titulo}</p>
        <p className="text-2xl font-bold text-gray-800 tracking-tight">{valor}</p>
      </div>
    </div>
  );
}