"use client";

import { useEffect, useState } from "react";
import services from "../../services/service";
import Inventory2OutlinedIcon from "@mui/icons-material/Inventory2Outlined";
import CheckCircleOutlineOutlinedIcon from "@mui/icons-material/CheckCircleOutlineOutlined";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";


/* =======================
   TIPOS
======================= */
type Regiao = {
  uf: string;
  disponivel: boolean;
  preco_formatado: string;
  preco_num: number;
  qtdDisponivel: number;
  valor_total: number;
  valor_total_formatado: string;
  mensagem?: string | null;
};

type Produto = {
  codigo: string;
  nome?: string;
  marca?: string;
  imagem?: string;
  disponivel?: boolean;
  status?: string;
  preco_formatado?: string;
  preco_num?: number;
  qtdDisponivel?: number;
  valor_total_formatado?: string;
  regioes?: Regiao[] | null;
  erro?: string;
};

/* =======================
   COMPONENTE
======================= */
export default function ConsultaPage() {
  const [produtos, setProdutos] = useState<Produto[]>([]);
  const [loading, setLoading] = useState(true);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [expandAll, setExpandAll] = useState(false);


  async function carregar() {
    setLoading(true);
    const result = await services("/produtos/consultar", { method: "GET" });

    if (result?.success) {
      setProdutos(result.data.dados_lote.itens || []);
    } else {
      alert("Erro ao carregar produtos");
    }

    setLoading(false);
  }



  useEffect(() => {
    carregar();
  }, []);



  /* =======================
     FILTROS
  ======================= */
  const produtosFiltrados = produtos.filter((p) => {
    const texto =
      `${p.codigo} ${p.nome ?? ""} ${p.marca ?? ""}`.toLowerCase();

    const matchBusca = texto.includes(search.toLowerCase());

    const matchStatus =
      !statusFilter ||
      (statusFilter === "disponivel" && p.disponivel && !p.erro) ||
      (statusFilter === "indisponivel" && !p.disponivel && !p.erro) ||
      (statusFilter === "erro" && !!p.erro);

    return matchBusca && matchStatus;
  });

  /* =======================
     KPIs
  ======================= */
  const total = produtos.length;
  const disponiveis = produtos.filter(p => p.disponivel && !p.erro).length;
  const indisponiveis = produtos.filter(p => !p.disponivel && !p.erro).length;
  const erros = produtos.filter(p => p.erro).length;

  function menorValor(regioes: Regiao[]) {
    const validos = regioes.filter(r => r.valor_total > 0);
    if (!validos.length) return null;
    return Math.min(...validos.map(r => r.valor_total));
  }

  if (loading) {
    return <div className="p-8 text-gray-500">Carregando produtos...</div>;
  }

  /* =======================
     RENDER
  ======================= */
  return (
    <div className="p-8 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">

        {/* ===== TÍTULO ===== */}
        <div className="mb-6">
          <h2 className="text-2xl font-semibold text-gray-800">
            Consulta de Produtos Recentes
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Visualização detalhada do último lote processado
          </p>
        </div>


        {/* ===== KPIs ===== */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <ResumoCard
            titulo="Total de Itens"
            valor={total}
            cor="indigo"
            icon={<Inventory2OutlinedIcon fontSize="medium" />}
          />
          <ResumoCard
            titulo="Disponíveis"
            valor={disponiveis}
            cor="emerald"
            icon={<CheckCircleOutlineOutlinedIcon fontSize="medium" />}
          />
          <ResumoCard
            titulo="Indisponíveis"
            valor={indisponiveis}
            cor="red"
            icon={<CancelOutlinedIcon fontSize="medium" />}
          />
          <ResumoCard
            titulo="Não Encontrados"
            valor={erros}
            cor="amber"
            icon={<ReportProblemOutlinedIcon fontSize="medium" />}
          />
        </div>


        {/* ===== BUSCA / FILTROS ===== */}
        <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-center">
            <input
              type="text"
              placeholder="Buscar por Código, Nome ou Marca..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="md:col-span-2 w-full px-4 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
            />

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg text-sm"
            >
              <option value="">Todos os Status</option>
              <option value="disponivel">Disponível</option>
              <option value="indisponivel">Indisponível</option>
              <option value="erro">Erro</option>
            </select>

            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-500">
                {produtosFiltrados.length} itens
              </span>

              <button
                onClick={() => {
                  setExpandAll(!expandAll);
                  setExpanded(expandAll ? null : "__ALL__");
                }}
                className="text-sm text-indigo-600 hover:text-indigo-800"
              >
                {expandAll ? "Recolher todos" : "Expandir todos"}
              </button>
            </div>
          </div>
        </div>

        {/* ===== TABELA ===== */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-100">
              <tr>
                <th className="px-4 py-3 text-left">Código</th>
                <th className="px-4 py-3 text-center">Imagem</th>
                <th className="px-4 py-3 text-left">Produto</th>
                <th className="px-4 py-3 text-right">Preço</th>
                <th className="px-4 py-3 text-center">Qtd</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th className="px-4 py-3 text-center">Status</th>
                <th className="px-4 py-3 text-center">Ações</th>
              </tr>
            </thead>

            <tbody>
              {produtosFiltrados.map((p) => {
                const aberto =
                  expanded === "__ALL__" || expanded === p.codigo;

                return (
                  <>
                    <tr
                      key={p.codigo}
                      className="border-t hover:bg-gray-50 transition"
                    >
                      <td className="px-4 py-4 font-medium">{p.codigo}</td>

                      <td className="px-4 py-4 text-center">
                        <img
                          src={
                            p.imagem ||
                            "https://isthmusblobs.blob.core.windows.net/imagens/foto-padrao.png"
                          }
                          className="w-12 h-12 object-contain mx-auto rounded-lg bg-gray-100 border"
                        />
                      </td>

                      <td className="px-4 py-4">
                        <div className="font-medium">{p.nome || "-"}</div>
                        <div className="text-xs text-gray-500 mt-1">
                          {p.marca || "-"}
                        </div>
                      </td>

                      <td className="px-4 py-4 text-right">
                        {p.preco_formatado || "R$ 0,00"}
                      </td>

                      <td className="px-4 py-4 text-center">
                        {p.qtdDisponivel || 0}
                      </td>

                      <td className="px-4 py-4 text-right font-semibold text-indigo-600">
                        {p.valor_total_formatado || "R$ 0,00"}
                      </td>

                      <td className="px-4 py-4 text-center">
                        {p.erro ? (
                          <span className="badge-red">Erro</span>
                        ) : p.disponivel ? (
                          <span className="badge-green">Disponível</span>
                        ) : (
                          <span className="badge-gray">Indisponível</span>
                        )}
                      </td>

                      <td className="px-4 py-4 text-center">
                        {p.regioes?.length ? (
                          <button
                            onClick={() =>
                              setExpanded(aberto ? null : p.codigo)
                            }
                            className=" inline-flex items-center gap-2
                                  px-3 py-1.5
                                  text-sm font-semibold
                                  rounded-md
                                  bg-indigo-600 text-white
                                  hover:bg-indigo-700
                                  transition"
                          >
                            {aberto ? "Ocultar" : "Ver detalhes"}
                          </button>
                        ) : (
                          <span className="text-xs text-gray-400">—</span>
                        )}
                      </td>
                    </tr>

                    {aberto && p.regioes && (
                      <tr className="bg-gray-50">
                        <td colSpan={8} className="px-6 py-6">
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            {p.regioes.map((r) => {
                              const menor = menorValor(p.regioes);

                              return (
                                <div
                                  key={r.uf}
                                  className={`rounded-xl border p-4 ${menor === r.valor_total
                                    ? "border-emerald-400 bg-emerald-50"
                                    : "border-gray-200 bg-white"
                                    }`}
                                >
                                  <div className="flex justify-between mb-2">
                                    <strong>{r.uf}</strong>
                                    {menor === r.valor_total && (
                                      <span className="badge-green">
                                        Melhor preço
                                      </span>
                                    )}
                                  </div>

                                  <div className="text-sm space-y-1">
                                    <div>Preço: {r.preco_formatado}</div>
                                    <div>Qtd: {r.qtdDisponivel}</div>
                                    <div className="font-semibold">
                                      Total: {r.valor_total_formatado}
                                    </div>
                                  </div>

                                  {r.mensagem && (
                                    <div className="text-xs text-gray-500 mt-2 whitespace-pre-line">
                                      {r.mensagem}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

/* =======================
   COMPONENTE KPI
======================= */
function ResumoCard({
  titulo,
  valor,
  cor,
  icon,
}: {
  titulo: string;
  valor: number;
  cor: "indigo" | "emerald" | "red" | "amber";
  icon: React.ReactNode;
}) {
  const cores: Record<string, string> = {
    indigo: "bg-indigo-50 text-indigo-700",
    emerald: "bg-emerald-50 text-emerald-700",
    red: "bg-red-50 text-red-700",
    amber: "bg-amber-50 text-amber-700",
  };

  const iconeBg: Record<string, string> = {
    indigo: "bg-indigo-100",
    emerald: "bg-emerald-100",
    red: "bg-red-100",
    amber: "bg-amber-100",
  };

  return (
    <div
      className={`rounded-xl p-4 flex items-center gap-4 shadow-sm border border-gray-100 ${cores[cor]}`}
    >
      {/* ÍCONE */}
      <div
        className={`p-3 rounded-lg flex items-center justify-center ${iconeBg[cor]}`}
      >
        {icon}
      </div>

      {/* TEXTO */}
      <div className="flex flex-col">
        <span className="text-sm font-medium text-gray-600">
          {titulo}
        </span>
        <span className="text-2xl font-semibold text-gray-900">
          {valor}
        </span>
      </div>
    </div>
  );
}

