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
} from "@mui/icons-material";

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
  regioes?: Regiao[];
};

type ProdutoComparado = {
  codigo: string;
  nome: string;
  imagem: string;
  fornecedor_vencedor: string;
  melhor_preco: number;
  melhor_preco_formatado: string;
  ofertas: Oferta[];
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
   HELPERS (FORMATAÇÃO)
======================= */
function formatBRL(value: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(value || 0);
}

function formatPercent(valueDecimal: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "percent",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(valueDecimal || 0);
}

/* =======================
   REGRA ICMS ST + FCP (COM SES)
   ICMS ST + FCP = (BC*18% + BC*2%) - SES(...)
   SES:
     - se AGREGADO MVA = 106,14% => CUSTO_ES * 4%
     - se AGREGADO MVA = 88,96%  => CUSTO_ES * 12%
     - se AGREGADO MVA = 0       => 0
======================= */
const AGREGADO_MVA_ES = 0.8896; // 88,96% (fixo, conforme seu cenário atual)

function approxEqual(a: number, b: number, tolerance = 0.00005) {
  return Math.abs(a - b) <= tolerance;
}

function calcSes(agregadoMvaDecimal: number, custoES: number) {
  if (approxEqual(agregadoMvaDecimal, 1.0614)) return custoES * 0.04; // 106,14%
  if (approxEqual(agregadoMvaDecimal, 0.8896)) return custoES * 0.12; // 88,96%
  if (approxEqual(agregadoMvaDecimal, 0)) return 0; // 0%
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

export default function ComparativoPrecosPage() {
  const router = useRouter();
  const { addToCart } = useCart();

  const [produtos, setProdutos] = useState<ProdutoComparado[]>([]);
  const [loading, setLoading] = useState(true);
  const [dataLote, setDataLote] = useState<string>("");
  const [dadosDesatualizados, setDadosDesatualizados] = useState(false);

  // Filtros
  const [search, setSearch] = useState("");
  const [selectedSupplier, setSelectedSupplier] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);

  // ✅ UF selecionada por (produto + fornecedor)
  const [regiaoSelecionada, setRegiaoSelecionada] = useState<Record<string, string>>({});

  /* =======================
      VERIFICAÇÃO DE DATA
  ======================= */
  const verificarData = (dataString: string) => {
    if (!dataString) return;

    const somenteData = dataString.split(" ")[0]; // "dd/mm/aaaa"
    const [dia, mes, ano] = somenteData.split("/").map(Number);
    const dataArquivo = new Date(ano, mes - 1, dia);

    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);

    setDadosDesatualizados(dataArquivo < hoje);
    setDataLote(dataString);
  };

  /* =======================
      CARREGAMENTO
  ======================= */
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
        result?.ultima_data_processamento ||
        result?.data?.ultima_data_processamento ||
        "";

      if (ultimaData) {
        verificarData(ultimaData);
      } else if (lista.length > 0) {
        const primeiraData = lista[0]?.ofertas[0]?.data_atualizacao;
        if (primeiraData) verificarData(primeiraData);
      }

      if (lista.length > 0) {
        // 4% OFF para portalcomdip + desconto nas regiões
        const listaComDesconto = lista.map((produto) => {
          const ofertasAtualizadas = produto.ofertas.map((oferta) => {
            if (oferta.fornecedor && oferta.fornecedor.toLowerCase() === "portalcomdip") {
              const precoOriginal = oferta.preco;
              const novoPreco = precoOriginal * 0.96;

              const regioesAtualizadas = oferta.regioes?.map((reg) => {
                const precoRegOriginal = reg.preco;
                const novoPrecoReg = precoRegOriginal * 0.96;

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
                regioes: regioesAtualizadas,
              };
            }

            return oferta;
          });

          // Recalcula vencedor após descontos
          const ofertasOrdenadas = [...ofertasAtualizadas].sort((a, b) => a.preco - b.preco);
          const melhorOferta = ofertasOrdenadas[0];

          return {
            ...produto,
            ofertas: ofertasAtualizadas,
            fornecedor_vencedor: melhorOferta ? melhorOferta.fornecedor : produto.fornecedor_vencedor,
            melhor_preco: melhorOferta ? melhorOferta.preco : produto.melhor_preco,
            melhor_preco_formatado: melhorOferta ? melhorOferta.preco_formatado : produto.melhor_preco_formatado,
          };
        });

        setProdutos(listaComDesconto);
      } else {
        setProdutos([]);
      }
    } catch (error) {
      console.error("Erro crítico ao carregar:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    carregar();
  }, []);

  /* =======================
      EXTRAÇÃO DE FORNECEDORES
  ======================= */
  const listaFornecedores = useMemo(() => {
    const fornecedoresSet = new Set<string>();
    produtos.forEach((p) => {
      p.ofertas?.forEach((o) => {
        if (o.fornecedor) fornecedoresSet.add(o.fornecedor);
      });
    });
    return Array.from(fornecedoresSet).sort();
  }, [produtos]);

  /* =======================
      FILTROS
  ======================= */
  const produtosFiltrados = produtos.filter((p) => {
    const termo = search.toLowerCase();

    const matchTexto =
      (p.codigo?.toLowerCase() || "").includes(termo) ||
      (p.nome?.toLowerCase() || "").includes(termo) ||
      (p.fornecedor_vencedor?.toLowerCase() || "").includes(termo);

    const matchFornecedor = selectedSupplier === "" || p.ofertas.some((o) => o.fornecedor === selectedSupplier);

    return matchTexto && matchFornecedor;
  });

  const totalProdutos = produtos.length;
  const totalOfertas = produtos.reduce((acc, p) => acc + (p.ofertas?.length || 0), 0);

  /* =======================
      RENDERIZAÇÃO
  ======================= */
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
        {/* HEADER */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 tracking-tight">Comparativo de Preços</h1>
            <p className="text-gray-500 mt-1">
              Análise em tempo real.
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

        {/* ALERTA DE DADOS DESATUALIZADOS */}
        {dadosDesatualizados && (
          <div className="bg-amber-50 border-l-4 border-amber-500 p-4 rounded-r shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <WarningAmberRounded className="text-amber-600 mt-0.5" />
              <div>
                <h3 className="font-bold text-amber-800">Atenção: Dados Desatualizados</h3>
                <p className="text-sm text-amber-700 mt-1">
                  Os dados exibidos são do dia <strong>{dataLote}</strong>. É recomendável atualizar para obter preços
                  precisos.
                </p>
              </div>
            </div>

            <button
              onClick={() => router.push("/upload")}
              className="whitespace-nowrap px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-sm font-bold rounded shadow-sm flex items-center gap-2 transition-colors"
            >
              <CloudUploadOutlined fontSize="small" />
              Fazer Upload Novo
            </button>
          </div>
        )}

        {/* KPIs */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <KpiCard
            titulo="Produtos Analisados"
            valor={totalProdutos}
            icon={<Inventory2Outlined className="text-indigo-600" />}
            bg="bg-indigo-50"
          />
          <KpiCard
            titulo="Total de Ofertas Encontradas"
            valor={totalOfertas}
            icon={<StorefrontOutlined className="text-emerald-600" />}
            bg="bg-emerald-50"
          />
        </div>

        {/* BARRA DE FERRAMENTAS */}
        <div className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex flex-col md:flex-row gap-4 items-center">
          {/* Busca */}
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

          {/* Filtro Fornecedor */}
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
            <FilterList className="text-gray-400" />
            <span>{produtosFiltrados.length} itens</span>
          </div>
        </div>

        {/* LISTA DE PRODUTOS */}
        <div className="space-y-4">
          {produtosFiltrados.map((produto) => {
            const isExpanded = expanded === produto.codigo;

            return (
              <div
                key={produto.codigo}
                className={`bg-white rounded-xl border transition-all duration-300 overflow-hidden
                  ${
                    isExpanded
                      ? "border-indigo-200 shadow-md ring-1 ring-indigo-50"
                      : "border-gray-200 shadow-sm hover:border-gray-300"
                  }
                `}
              >
                {/* CABEÇALHO */}
                <div
                  className="p-5 flex flex-col md:flex-row items-center gap-6 cursor-pointer"
                  onClick={() => setExpanded(isExpanded ? null : produto.codigo)}
                >
                  <div className="flex-shrink-0 w-16 h-16 md:w-20 md:h-20 bg-gray-100 rounded-lg border border-gray-100 p-2 flex items-center justify-center">
                    <img
                      src={produto.imagem || "https://via.placeholder.com/150"}
                      alt={produto.nome}
                      className="w-full h-full object-contain mix-blend-multiply"
                      onError={(e) => (e.currentTarget.src = "https://via.placeholder.com/150")}
                    />
                  </div>

                  <div className="flex-1 text-center md:text-left overflow-hidden w-full">
                    <div className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">{produto.codigo}</div>
                    <h3 className="text-lg font-semibold text-gray-900 leading-tight truncate">{produto.nome}</h3>
                    <div className="mt-1 text-sm text-gray-500">{(produto.ofertas || []).length} ofertas encontradas</div>
                  </div>

                  <div className="text-center md:text-right min-w-[140px]">
                    <div className="text-xs text-gray-500 mb-1">Melhor oferta</div>
                    <div className="text-xl md:text-2xl font-bold text-emerald-600">{produto.melhor_preco_formatado}</div>
                    <div className="text-xs font-medium text-indigo-600 mt-1 truncate max-w-[150px] mx-auto md:ml-auto">
                      {produto.fornecedor_vencedor}
                    </div>
                  </div>

                  <div className="hidden md:block text-gray-400">{isExpanded ? <ExpandLess /> : <ExpandMore />}</div>
                </div>

                {/* DETALHES */}
                <div
                  className={`border-t border-gray-100 bg-gray-50 transition-all duration-300 ease-in-out
                    ${isExpanded ? "max-h-[1000px] opacity-100" : "max-h-0 opacity-0 hidden"}
                  `}
                >
                  <div className="p-5 md:p-8">
                    <h4 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
                      <StorefrontOutlined fontSize="small" /> Lista de Fornecedores
                    </h4>

                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                      {(produto.ofertas || []).map((oferta, idx) => {
                        const isWinner = oferta.fornecedor === produto.fornecedor_vencedor;
                        const isSelectedSupplier = selectedSupplier === oferta.fornecedor;

                        const keyOferta = `${produto.codigo}-${oferta.fornecedor}`;
                        const ufEscolhida = regiaoSelecionada[keyOferta];
                        const precisaSelecionarUF = (oferta.regioes?.length || 0) > 1 && !ufEscolhida;

                        // ✅ UF atual para efeitos de preço original dinâmico
                        const ufAtual =
                          regiaoSelecionada[keyOferta] ||
                          (oferta.regioes?.length === 1 ? oferta.regioes?.[0]?.uf : "") ||
                          "";

                        const regSelecionada = oferta.regioes?.find((r) => r.uf === ufAtual);

                        // ✅ Preço original dinâmico (por UF selecionada)
                        // prioridade: preço_original da UF selecionada -> preço_original geral da oferta
                        const precoOriginalDinamico =
                          (regSelecionada?.preco_original ?? oferta.preco_original) || 0;

                        // ✅ Exibe desconto somente se houver original (UF ou geral) maior que o preço atual correspondente
                        const deveMostrarOriginal =
                          !!(regSelecionada?.preco_original || oferta.preco_original) && precoOriginalDinamico > 0;

                        // ✅ ES (somente ES): se existir na lista de regiões, exibe o box de cálculo
                        const regES = oferta.regioes?.find((r) => (r.uf || "").toUpperCase() === "ES");
                        const calcES = regES ? calcTributosES(regES.preco) : null;

                        return (
                          <div
                            key={idx}
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
                              <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-500 text-white text-[10px] font-bold px-3 py-1 rounded-full uppercase tracking-wide flex items-center gap-1 shadow-sm">
                                <EmojiEventsOutlined style={{ fontSize: 14 }} /> Melhor Preço
                              </div>
                            )}

                            <div>
                              <div
                                className={`font-semibold text-sm mb-1 truncate ${isWinner ? "text-emerald-700" : "text-gray-800"}`}
                                title={oferta.fornecedor}
                              >
                                {oferta.fornecedor}
                              </div>

                              <div className="text-xs text-gray-400 flex items-center gap-1 mb-2">
                                <AccessTimeOutlined style={{ fontSize: 12 }} /> {oferta.data_atualizacao}
                              </div>
                            </div>

                            {/* REGIÕES COM SELEÇÃO */}
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
                                      <label key={reg.uf} className="flex justify-between items-center text-xs cursor-pointer select-none">
                                        <div className="flex items-center gap-2">
                                          <input
                                            type="radio"
                                            name={`reg-${keyOferta}`}
                                            checked={checked}
                                            onChange={() =>
                                              setRegiaoSelecionada((prev) => ({
                                                ...prev,
                                                [keyOferta]: reg.uf,
                                              }))
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
                                            <span className={`font-semibold ${isWinner ? "text-emerald-700" : "text-gray-800"}`}>
                                              {reg.preco_formatado}
                                            </span>
                                          </div>
                                        </div>
                                      </label>
                                    );
                                  })}
                                </div>

                                {precisaSelecionarUF && (
                                  <p className="mt-2 text-[11px] text-amber-700 font-semibold">
                                    Selecione a UF para adicionar ao carrinho.
                                  </p>
                                )}

                                {/* ✅ BOX ES (somente ES) - EXIBE APENAS OS CAMPOS PEDIDOS */}
                                {regES && calcES && (
                                  <div className="mt-3 bg-white border border-indigo-100 rounded-lg p-3">
                                    <div className="text-[10px] font-bold text-indigo-700 uppercase tracking-wide mb-2">
                                      ES — Cálculo Tributário
                                    </div>

                                    <div className="grid grid-cols-2 gap-2 text-[12px]">
                                      <div className="bg-gray-50 rounded p-2 border border-gray-100">
                                        <div className="text-[10px] text-gray-500 font-bold uppercase">(AGREGADO) MVA</div>
                                        <div className="font-semibold text-gray-800">{formatPercent(calcES.agregadoMva)}</div>
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
                                        <div className="font-semibold text-gray-800">{formatBRL(calcES.icmsStMaisFcp)}</div>
                                      </div>

                                      <div className="col-span-2 bg-indigo-50 rounded p-2 border border-indigo-100">
                                        <div className="text-[10px] text-indigo-700 font-bold uppercase">
                                          CUSTO MERCADORIA (ES)
                                        </div>
                                        <div className="text-lg font-extrabold text-indigo-700">
                                          {formatBRL(calcES.custoMercadoria)}
                                        </div>
                                        <div className="mt-1 text-[10px] text-indigo-700/80">
                                          Fórmula: CUSTO ES + (ICMS ST + FCP)
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
                                  <span className="block text-[10px] text-gray-500 uppercase">Estoque Total</span>
                                  <span className={`text-sm font-medium ${oferta.estoque > 0 ? "text-gray-700" : "text-red-400"}`}>
                                    {oferta.estoque} un
                                  </span>
                                </div>

                                <div className="text-right">
                                  {/* ✅ Desconto: preço original dinâmico por UF selecionada */}
                                  {deveMostrarOriginal && (
                                    <div className="flex flex-col items-end mb-1">
                                      {oferta.teve_desconto && (
                                        <span className="text-[10px] bg-indigo-100 text-indigo-700 px-1.5 py-0.5 rounded font-bold uppercase tracking-wide">
                                          4% OFF
                                        </span>
                                      )}

                                      <span className="text-xs text-gray-400 line-through decoration-gray-400">
                                        {formatBRL(precoOriginalDinamico)}
                                      </span>
                                    </div>
                                  )}

                                  <span className={`text-lg font-bold ${isWinner ? "text-emerald-600" : "text-gray-700"}`}>
                                    {oferta.preco_formatado}
                                  </span>
                                </div>
                              </div>

                              {/* BOTÃO ADICIONAR AO CARRINHO */}
                              <button
                                disabled={precisaSelecionarUF}
                                onClick={(e) => {
                                  e.stopPropagation();

                                  const ufFinal =
                                    regiaoSelecionada[keyOferta] ||
                                    (oferta.regioes?.length === 1 ? oferta.regioes?.[0]?.uf : "") ||
                                    "";

                                  const regObj = oferta.regioes?.find((r) => r.uf === ufFinal);
                                  const precoFinal = regObj?.preco ?? oferta.preco;
                                  const precoOriginalFinal = regObj?.preco_original ?? oferta.preco_original;

                                  addToCart({
                                    uid: `${produto.codigo}-${oferta.fornecedor}-${ufFinal || "GERAL"}`,
                                    codigo: produto.codigo,
                                    nome: produto.nome,
                                    imagem: produto.imagem,
                                    fornecedor: oferta.fornecedor,
                                    preco: precoFinal,
                                    quantidade: 1,
                                    uf: ufFinal || undefined,
                                    origem: regObj ? "REGIAO" : "OFERTA_GERAL",
                                    teve_desconto: !!(regObj?.preco_original || oferta.preco_original),
                                    preco_original: precoOriginalFinal,
                                  });
                                }}
                                className={`w-full py-2 px-3 rounded-lg flex items-center justify-center gap-2 text-sm font-bold transition-all
                                  ${
                                    precisaSelecionarUF
                                      ? "bg-gray-200 text-gray-500 cursor-not-allowed"
                                      : isWinner
                                      ? "bg-emerald-600 hover:bg-emerald-700 text-white shadow-emerald-200 shadow-md"
                                      : "bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-100"
                                  }
                                `}
                              >
                                <AddShoppingCart fontSize="small" />
                                Adicionar
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}

          {produtosFiltrados.length === 0 && !loading && (
            <div className="text-center py-20 bg-white rounded-xl border border-dashed border-gray-300">
              <p className="text-gray-400">Nenhum produto encontrado com os filtros atuais.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// KPI CARD
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
