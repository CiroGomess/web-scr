"use client";

import { useState } from "react";
import { useCart } from "../../contexts/CartContext";
import { DeleteOutline, Storefront, ArrowBack } from "@mui/icons-material";
import { useRouter } from "next/navigation";
// Importamos o Modal que criamos para gerenciar os links externos
import CheckoutModal from "../../components/cart/CheckoutModal"; 

export default function CarrinhoPage() {
  const { cart, removeFromCart, clearCart } = useCart();
  const router = useRouter();

  // Estados para controlar o Modal de Finalização
  const [modalOpen, setModalOpen] = useState(false);
  const [checkoutData, setCheckoutData] = useState<{ fornecedor: string, itens: typeof cart } | null>(null);

  // Lógica para agrupar itens por Fornecedor
  const itensPorFornecedor = cart.reduce((acc, item) => {
    if (!acc[item.fornecedor]) acc[item.fornecedor] = [];
    acc[item.fornecedor].push(item);
    return acc;
  }, {} as Record<string, typeof cart>);

  const valorTotalGeral = cart.reduce((acc, item) => acc + (item.preco * item.quantidade), 0);

  // Função chamada ao clicar em "Enviar Pedido"
  const handleEnviarPedido = (fornecedor: string, itens: typeof cart) => {
    setCheckoutData({ fornecedor, itens });
    setModalOpen(true);
  };

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
            Meu Carrinho <span className="text-lg font-normal text-gray-500 bg-gray-200 px-2 py-0.5 rounded-full text-sm">{cart.length} itens</span>
            </h1>
            <button onClick={() => router.push("/consulta")} className="text-indigo-600 font-medium hover:underline text-sm">
                Continuar comprando
            </button>
        </div>

        <div className="space-y-8">
          {Object.entries(itensPorFornecedor).map(([fornecedor, itens]) => {
            const totalFornecedor = itens.reduce((acc, i) => acc + (i.preco * i.quantidade), 0);

            return (
              <div key={fornecedor} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
                {/* Cabeçalho do Fornecedor */}
                <div className="bg-indigo-50/50 p-4 border-b border-gray-200 flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <Storefront className="text-indigo-600" />
                    <h3 className="font-bold text-lg text-gray-800">{fornecedor}</h3>
                  </div>
                  <div className="text-sm text-gray-600">
                    Subtotal Loja: <span className="font-bold text-gray-900 ml-1">{new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(totalFornecedor)}</span>
                  </div>
                </div>

                {/* Lista de Itens */}
                <div className="divide-y divide-gray-100">
                  {itens.map((item) => (
                    <div key={item.uid} className="p-4 flex flex-col sm:flex-row items-center gap-4 hover:bg-gray-50 transition">
                      <img src={item.imagem} alt={item.nome} className="w-16 h-16 object-contain rounded border border-gray-100 bg-white p-1" />
                      
                      <div className="flex-1 text-center sm:text-left">
                        <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">{item.codigo}</p>
                        <h4 className="font-medium text-gray-800 line-clamp-1">{item.nome}</h4>
                        <p className="text-sm text-gray-500 mt-1">
                          {item.quantidade}x {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.preco)}
                        </p>
                      </div>

                      <div className="text-right flex flex-col items-end">
                        <div className="font-bold text-gray-900 text-lg">
                          {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(item.preco * item.quantidade)}
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
                    onClick={() => handleEnviarPedido(fornecedor, itens)}
                    className="w-full sm:w-auto px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-bold rounded shadow-sm transition"
                  >
                    Enviar Pedido para {fornecedor}
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        {/* Resumo Final */}
        <div className="mt-8 bg-white p-6 rounded-xl shadow-lg border border-indigo-100 flex flex-col md:flex-row justify-between items-center gap-6 sticky bottom-4">
          <div>
            <p className="text-gray-500 text-sm">Valor Total Estimado</p>
            <p className="text-3xl font-bold text-indigo-700">
              {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valorTotalGeral)}
            </p>
          </div>
          <div className="flex gap-3 w-full md:w-auto">
             <button 
               onClick={clearCart}
               className="flex-1 md:flex-none px-6 py-3 border border-red-200 text-red-600 font-bold rounded-lg hover:bg-red-50 transition"
             >
               Limpar Carrinho
             </button>
             {/* Nota: O botão "Finalizar Tudo" pode ser complexo pois cada fornecedor tem um link diferente.
                Por enquanto, ele não tem ação definida ou poderia abrir um alerta.
             */}
             <button className="flex-1 md:flex-none px-8 py-3 bg-green-600 text-white font-bold rounded-lg hover:bg-green-700 shadow-lg hover:shadow-green-200 transition">
               Finalizar Tudo
             </button>
          </div>
        </div>
      </div>

      {/* RENDERIZAÇÃO DO MODAL DE CHECKOUT */}
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