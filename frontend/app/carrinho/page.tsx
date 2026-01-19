"use client";

import { useState, useMemo } from "react";
import { useCart } from "../../contexts/CartContext";
import {
  DeleteOutline,
  Storefront,
  ArrowBack,
  LocalOfferOutlined,
} from "@mui/icons-material";
import { useRouter } from "next/navigation";
import CheckoutModal from "../../components/cart/CheckoutModal";
import Swal from "sweetalert2";

export default function CarrinhoPage() {
  const { cart, removeFromCart, updateQuantity, clearCart } = useCart() as any;
  const router = useRouter();

  const [modalOpen, setModalOpen] = useState(false);
  const [checkoutData, setCheckoutData] = useState<{
    fornecedor: string;
    itens: typeof cart;
  } | null>(null);

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

  // ✅ Função segura para atualizar pelos botões (+ e -)
  const handleBotaoQtd = (uid: string, novaQtd: number) => {
    if (novaQtd < 1) return;
    updateQuantity(uid, novaQtd);
  };

  // ✅ Limpar carrinho com confirmação
  const handleLimparCarrinho = async () => {
    const res = await Swal.fire({
      title: "Limpar carrinho?",
      text: "Essa ação vai remover todos os itens do carrinho. Deseja continuar?",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Sim, limpar",
      cancelButtonText: "Cancelar",
      confirmButtonColor: "#4f46e5",
      cancelButtonColor: "#6b7280",
    });

    if (res.isConfirmed) {
      clearCart();
      await Swal.fire({
        title: "Carrinho limpo!",
        text: "Todos os itens foram removidos.",
        icon: "success",
        confirmButtonText: "OK",
        confirmButtonColor: "#4f46e5",
      });
    }
  };

  // ===========================
  // CÁLCULOS DO DASHBOARD
  // ===========================
  const dashFornecedores = useMemo(() => {
    const entries = Object.entries(itensPorFornecedor).map(([fornecedor, itens]) => {
      const qtdProdutos = (itens as any[]).reduce((acc, i) => acc + (i.quantidade || 0), 0);
      const subtotal = (itens as any[]).reduce((acc, i) => acc + i.preco * i.quantidade, 0);

      const descontoValor = (itens as any[]).reduce((acc, i) => {
        const original = typeof i.preco_original === "number" ? i.preco_original : null;
        if (original === null) return acc;
        const diff = Math.max(0, (original - i.preco) * (i.quantidade || 0));
        return acc + diff;
      }, 0);

      const totalComDesconto = subtotal;
      const descontoPct = subtotal > 0 ? descontoValor / (subtotal + descontoValor) : 0;

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
          className="px-6 py-2 bg-#004382-600 text-white rounded-lg hover:bg-#225DA9-700 transition flex items-center gap-2"
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
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-2">
              Meu Carrinho{" "}
              <span className="text-lg font-normal text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full text-sm">
                {cart.length} itens
              </span>
            </h1>

            {/* ✅ Botão Limpar Carrinho */}
            <button
              onClick={handleLimparCarrinho}
              className="px-4 py-2 text-sm font-bold rounded-lg border border-red-200 bg-red-50 text-red-600 hover:bg-red-100 transition"
            >
              Limpar carrinho
            </button>
          </div>

          <button
            onClick={() => router.push("/consulta")}
            className="text-indigo-600 font-medium hover:underline text-sm"
          >
            Continuar comprando
          </button>
        </div>

        {/* DASHBOARD */}
        <div className="mb-8">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="p-4 md:p-5 border-b border-gray-200 flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
              <div>
                <p className="text-sm text-gray-500">Resumo por fornecedor</p>
                <h2 className="text-xl font-bold text-gray-900">Distribuição de itens e custos</h2>
              </div>
              <div className="text-right">
                <p className="text-xs text-gray-500">Total geral (valores finais)</p>
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
                          <p className="text-xs text-gray-500">{e.qtdProdutos} un</p>
                        </div>
                      </div>
                      {e.descontoValor > 0 && (
                        <span className="text-[11px] font-bold bg-green-100 text-green-700 px-2 py-1 rounded-full">
                          desconto aplicado
                        </span>
                      )}
                    </div>
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">Total</span>
                        <span className="font-extrabold text-indigo-700">
                          {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
                            e.totalComDesconto
                          )}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* LISTA DE ITENS */}
        <div className="space-y-8">
          {Object.entries(itensPorFornecedor).map(([fornecedor, itens]) => {
            const totalFornecedor = (itens as any[]).reduce((acc, i) => acc + i.preco * i.quantidade, 0);

            return (
              <div key={fornecedor} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                <div className="bg-indigo-50/50 p-4 border-b border-gray-200 flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <Storefront className="text-indigo-600" />
                    <h3 className="font-bold text-lg text-gray-800">{fornecedor}</h3>
                  </div>
                  <div className="text-right">
                    <span className="font-extrabold text-indigo-700 text-lg">
                      {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(totalFornecedor)}
                    </span>
                  </div>
                </div>

                <div className="divide-y divide-gray-100">
                  {(itens as any[]).map((item) => (
                    <div
                      key={item.uid}
                      className="p-4 flex flex-col sm:flex-row items-center gap-4 hover:bg-gray-50 transition"
                    >
                      <img
                        src={item.imagem}
                        alt={item.nome}
                        className="w-16 h-16 object-contain rounded border border-gray-100 bg-white p-1"
                      />

                      <div className="flex-1 text-center sm:text-left">
                        <div className="flex flex-col sm:flex-row sm:items-center gap-2 mb-1 justify-center sm:justify-start">
                          <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">{item.codigo}</span>

                          {item.marca && (
                            <span className="flex items-center gap-1 text-[9px] text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-100 font-semibold">
                              <LocalOfferOutlined style={{ fontSize: 10 }} /> {item.marca}
                            </span>
                          )}
                        </div>

                        <h4 className="font-medium text-gray-800 line-clamp-1">{item.nome}</h4>

                        {item.uf && (
                          <p className="text-xs text-gray-500 mt-1">
                            Região (UF): <span className="font-bold text-gray-700">{item.uf}</span>
                          </p>
                        )}

                        <div className="mt-1 flex items-center justify-center sm:justify-start gap-2">
                          <span className="text-sm text-gray-600">
                            {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(item.preco)}
                            <span className="text-xs text-gray-400 ml-1">/ un</span>
                          </span>
                        </div>
                      </div>

                      <div className="text-right flex flex-col items-center sm:items-end gap-2">
                        <div className="flex items-center gap-2 bg-white border border-gray-200 rounded-lg p-1">
                          <button
                            onClick={() => handleBotaoQtd(item.uid, Number(item.quantidade) - 1)}
                            className="w-8 h-8 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded text-gray-600 font-bold disabled:opacity-50"
                            disabled={item.quantidade <= 1}
                          >
                            -
                          </button>

                          <input
                            type="number"
                            min="1"
                            key={item.quantidade}
                            defaultValue={item.quantidade}
                            onBlur={(e) => {
                              let val = parseInt(e.target.value);
                              if (isNaN(val) || val < 1) val = 1;
                              if (val !== item.quantidade) {
                                updateQuantity(item.uid, val);
                              }
                            }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                e.currentTarget.blur();
                              }
                            }}
                            className="w-12 text-center text-sm font-semibold text-gray-800 outline-none appearance-none"
                          />

                          <button
                            onClick={() => handleBotaoQtd(item.uid, Number(item.quantidade) + 1)}
                            className="w-8 h-8 flex items-center justify-center bg-gray-100 hover:bg-gray-200 rounded text-gray-600 font-bold"
                          >
                            +
                          </button>
                        </div>

                        <div className="font-bold text-gray-900 text-lg">
                          {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(
                            item.preco * item.quantidade
                          )}
                        </div>

                        <button
                          onClick={() => removeFromCart(item.uid)}
                          className="text-red-500 hover:text-red-700 text-xs flex items-center gap-1 transition"
                        >
                          <DeleteOutline fontSize="small" /> Remover item
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

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

        {checkoutData && (
          <CheckoutModal
            open={modalOpen}
            onClose={() => setModalOpen(false)}
            fornecedor={checkoutData.fornecedor}
            itens={checkoutData.itens}
          />
        )}
      </div>
    </div>
  );
}
