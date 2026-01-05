"use client";

import { useState, useMemo } from "react";
import { useCart } from "../../contexts/CartContext";
import { DeleteOutline, Storefront, ArrowBack } from "@mui/icons-material";
import { useRouter } from "next/navigation";
import CheckoutModal from "../../components/cart/CheckoutModal";

export default function CarrinhoPage() {
  const { cart, removeFromCart, clearFromCart, clearCart } = useCart() as any;
  const router = useRouter();

  const [modalOpen, setModalOpen] = useState(false);
  const [checkoutData, setCheckoutData] = useState<{ fornecedor: string; itens: typeof cart } | null>(null);

  // Agrupa por fornecedor
  const itensPorFornecedor = cart.reduce((acc: any, item: any) => {
    if (!acc[item.fornecedor]) acc[item.fornecedor] = [];
    acc[item.fornecedor].push(item);
    return acc;
  }, {} as Record<string, typeof cart>);

  const handleEnviarPedido = (fornecedor: string, itens: typeof cart) => {
    setCheckoutData({ fornecedor, itens });
    setModalOpen(true);
  };

  // ===========================
  // DASH RESUMO POR FORNECEDOR
  // DESCONTO: SOMENTE PORTALCOMDIP (4%)
  // ===========================
  const dashFornecedores = useMemo(() => {
    const entries = Object.entries(itensPorFornecedor).map(([fornecedor, itens]) => {
      const qtdProdutos = (itens as any[]).reduce((acc, i) => acc + (i.quantidade || 0), 0);
      const subtotal = (itens as any[]).reduce((acc, i) => acc + i.preco * i.quantidade, 0);

      const fornecedorLower = (fornecedor || "").toString().toLowerCase().trim();
      const isPortalComDip =
        fornecedorLower === "portalcomdip" ||
        fornecedorLower.includes("portalcomdip") ||
        fornecedorLower.includes("portal com dip");

      const descontoPct = isPortalComDip ? 0.04 : 0;
      const descontoValor = subtotal * descontoPct;
      const totalComDesconto = subtotal - descontoValor;

      return {
        fornecedor: fornecedor as string,
        qtdProdutos,
        subtotal,
        descontoPct,
        descontoValor,
        totalComDesconto,
      };
    });

    entries.sort((a, b) => b.totalComDesconto - a.totalComDesconto);

    const totalGeralComDescontos = entries.reduce((acc, e) => acc + e.totalComDesconto, 0);

    return { entries, totalGeralComDescontos };
  }, [itensPorFornecedor]);

  // Layout vazio
  if (cart.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
        <div className="bg-white p-6 rounded-full shadow-sm mb-4">
          <Storefront className="text-gray-300" style={{ fontSize: 60 }} />
        </div>
        <h2 className="text-2xl font-bold text-gray-800">Seu carrinho está vazio</h2>
        <p className="text-gray-500 mb-6 mt-2">Adicione produtos da tela de consulta para começar.</p>
        <button
          onClick={() => router.push("/consulta")}
          className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition flex items-center gap-2"
        >
          <ArrowBack fontSize="small" /> Voltar para Consultas
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6 md:p-10 font-sans">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
            Meu Carrinho{" "}
            <span className="text-lg font-normal text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full text-sm">
              {cart.length} itens
            </span>
          </h1>
          <button onClick={() => router.push("/consulta")} className="text-indigo-600 font-medium hover:underline text-sm">
            Continuar comprando
          </button>
        </div>

        {/* ===========================
            DASH / RESUMO POR FORNECEDOR
           =========================== */}
        <div className="mb-8">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 md:p-5 border-b border-gray-200 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
              <div>
                <p className="text-sm text-gray-500">Resumo por fornecedor</p>
                <h2 className="text-xl font-bold text-gray-900">Distribuição de itens e custos</h2>
              </div>

              <div className="text-right">
                <p className="text-xs text-gray-500">Total geral (com descontos aplicáveis)</p>
                <p className="text-2xl font-bold text-indigo-700">
                  {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
                    dashFornecedores.totalGeralComDescontos
                  )}
                </p>
              </div>
            </div>

            <div className="p-4 md:p-5">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {dashFornecedores.entries.map((e) => (
                  <div
                    key={e.fornecedor}
                    className="rounded-xl border border-gray-200 bg-gray-50 p-4 hover:bg-gray-100 transition"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Storefront className="text-indigo-600" />
                        <div>
                          <p className="font-bold text-gray-900 leading-tight">{e.fornecedor}</p>
                          <p className="text-xs text-gray-500">
                            {e.qtdProdutos} {e.qtdProdutos === 1 ? "unidade" : "unidades"}
                          </p>
                        </div>
                      </div>

                      {e.descontoPct > 0 && (
                        <span className="text-[11px] font-bold bg-green-100 text-green-700 px-2 py-1 rounded-full">
                          -{Math.round(e.descontoPct * 100)}% desconto
                        </span>
                      )}
                    </div>

                    <div className="mt-4 space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Subtotal</span>
                        <span className="font-bold text-gray-900">
                          {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(e.subtotal)}
                        </span>
                      </div>

                      {e.descontoPct > 0 && (
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600">Desconto</span>
                          <span className="font-bold text-green-700">
                            -{" "}
                            {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(e.descontoValor)}
                          </span>
                        </div>
                      )}

                      <div className="flex items-center justify-between text-sm pt-2 border-t border-gray-200">
                        <span className="text-gray-700 font-medium">Total</span>
                        <span className="font-extrabold text-indigo-700">
                          {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(e.totalComDesconto)}
                        </span>
                      </div>

                      {e.descontoPct > 0 && (
                        <p className="text-[11px] text-gray-500 pt-1">
                          Desconto aplicado automaticamente para <span className="font-bold">{e.fornecedor}</span>.
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <p className="text-xs text-gray-500 mt-4">
                Observação: o desconto de 4% é aplicado apenas ao fornecedor <span className="font-bold">portalcomdip</span>.
              </p>
            </div>
          </div>
        </div>

        {/* ===========================
            LISTA DE FORNECEDORES / ITENS
           =========================== */}
        <div className="space-y-8">
          {Object.entries(itensPorFornecedor).map(([fornecedor, itens]) => {
            const subtotalFornecedor = (itens as any[]).reduce((acc, i) => acc + i.preco * i.quantidade, 0);

            const fornecedorLower = (fornecedor || "").toString().toLowerCase().trim();
            const isPortalComDip =
              fornecedorLower === "portalcomdip" ||
              fornecedorLower.includes("portalcomdip") ||
              fornecedorLower.includes("portal com dip");

            const descontoPct = isPortalComDip ? 0.04 : 0;
            const descontoValor = subtotalFornecedor * descontoPct;
            const totalFornecedor = subtotalFornecedor - descontoValor;

            return (
              <div key={fornecedor} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                {/* Cabeçalho do Fornecedor */}
                <div className="bg-indigo-50/50 p-4 border-b border-gray-200 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
                  <div className="flex items-center gap-2">
                    <Storefront className="text-indigo-600" />
                    <h3 className="font-bold text-lg text-gray-800">{fornecedor}</h3>

                    {descontoPct > 0 && (
                      <span className="text-[11px] font-bold bg-green-100 text-green-700 px-2 py-1 rounded-full">
                        -{Math.round(descontoPct * 100)}% desconto
                      </span>
                    )}
                  </div>

                  <div className="text-sm text-gray-600 text-right">
                    <div>
                      Subtotal:{" "}
                      <span className="font-bold text-gray-900 ml-1">
                        {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(subtotalFornecedor)}
                      </span>
                    </div>

                    {descontoPct > 0 && (
                      <div>
                        Desconto:{" "}
                        <span className="font-bold text-green-700 ml-1">
                          -{" "}
                          {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(descontoValor)}
                        </span>
                      </div>
                    )}

                    <div>
                      Total:{" "}
                      <span className="font-extrabold text-indigo-700 ml-1">
                        {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(totalFornecedor)}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Lista de Itens */}
                <div className="divide-y divide-gray-100">
                  {(itens as any[]).map((item) => (
                    <div key={item.uid} className="p-4 flex flex-col sm:flex-row items-center gap-4 hover:bg-gray-50 transition">
                      <img
                        src={item.imagem}
                        alt={item.nome}
                        className="w-16 h-16 object-contain rounded border border-gray-100 bg-white p-1"
                      />

                      <div className="flex-1 text-center sm:text-left">
                        <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">{item.codigo}</p>
                        <h4 className="font-medium text-gray-800 line-clamp-1">{item.nome}</h4>
                        <p className="text-sm text-gray-500 mt-1">
                          {item.quantidade}x{" "}
                          {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(item.preco)}
                        </p>
                      </div>

                      <div className="text-right flex flex-col items-end">
                        <div className="font-bold text-gray-900 text-lg">
                          {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
                            item.preco * item.quantidade
                          )}
                        </div>
                        <button
                          onClick={() => removeFromCart(item.uid)}
                          className="text-red-500 hover:text-red-700 text-xs mt-1 flex items-center gap-1 transition"
                        >
                          <DeleteOutline fontSize="small" /> Remover item
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Botão de Enviar Pedido Específico */}
                <div className="p-4 bg-gray-50 border-t border-gray-200 text-right">
                  <button
                    onClick={() => handleEnviarPedido(fornecedor, itens as any)}
                    className="w-full sm:w-auto px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded shadow-sm transition"
                  >
                    Enviar Pedido para {fornecedor}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* ===========================
            AÇÕES DO CARRINHO (SEM VALOR TOTAL ESTIMADO)
           =========================== */}
       
      </div>

      {checkoutData && (
        <CheckoutModal
          open={modalOpen}
          onClose={() => setModalOpen(false)}
          fornecedor={checkoutData.fornecedor}
          itens={checkoutData.itens}
        />
      )}
    </div>
  );
}
