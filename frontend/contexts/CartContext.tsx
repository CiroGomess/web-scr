"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

// Definição do item do carrinho
export type CartItem = {
  uid: string; // ID único (codigo + fornecedor + uf) para diferenciar ofertas/UF
  codigo: string;
  nome: string;
  imagem: string;
  marca?: string; // ✅ NOVO CAMPO: Adicionado para salvar a marca
  fornecedor: string;
  preco: number;
  quantidade: number;

  // ✅ NOVOS CAMPOS (para mostrar a região no carrinho)
  uf?: string; // Ex: "SP", "RJ", ...
  origem?: "REGIAO" | "OFERTA_GERAL" | string;

  // ✅ Para evitar desconto duplicado no carrinho e permitir exibição
  preco_original?: number; // preço antes do desconto (se existir)
  teve_desconto?: boolean;
};

type CartContextType = {
  cart: CartItem[];
  addToCart: (item: CartItem) => void;
  removeFromCart: (uid: string) => void;
  updateQuantity: (uid: string, quantidade: number) => void; // ✅ NOVA FUNÇÃO
  clearCart: () => void;
  cartCount: number;
};

const CartContext = createContext<CartContextType>({} as CartContextType);

export function CartProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<CartItem[]>([]);

  // Carregar do LocalStorage ao iniciar
  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const savedCart = localStorage.getItem("carrinho_compras");
        if (savedCart) {
          const parsed = JSON.parse(savedCart);
          if (Array.isArray(parsed)) {
            setCart(parsed);
          } else {
            setCart([]);
          }
        }
      } catch (err) {
        console.error("Erro ao carregar carrinho do localStorage:", err);
        setCart([]);
      }
    }
  }, []);

  // Salvar no LocalStorage sempre que mudar
  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem("carrinho_compras", JSON.stringify(cart));
      } catch (err) {
        console.error("Erro ao salvar carrinho no localStorage:", err);
      }
    }
  }, [cart]);

  const addToCart = (newItem: CartItem) => {
    setCart((prev) => {
      // Verifica se o item já existe (mesmo uid)
      const exists = prev.find((item) => item.uid === newItem.uid);

      if (exists) {
        return prev.map((item) =>
          item.uid === newItem.uid
            ? { ...item, quantidade: (item.quantidade || 0) + (newItem.quantidade || 1) }
            : item
        );
      }

      // Se vier sem quantidade, garante 1
      const itemToAdd: CartItem = {
        ...newItem,
        quantidade: newItem.quantidade && newItem.quantidade > 0 ? newItem.quantidade : 1,
      };

      return [...prev, itemToAdd];
    });
  };

  const removeFromCart = (uid: string) => {
    setCart((prev) => prev.filter((item) => item.uid !== uid));
  };

  // ✅ NOVA FUNÇÃO: Atualiza a quantidade diretamente (para o input manual)
  const updateQuantity = (uid: string, quantidade: number) => {
    setCart((prev) =>
      prev.map((item) =>
        // Math.max(1, ...) garante que nunca fique 0 ou negativo
        item.uid === uid ? { ...item, quantidade: Math.max(1, quantidade) } : item
      )
    );
  };

  const clearCart = () => {
    setCart([]);
  };

  const cartCount = cart.reduce((acc, item) => acc + (item.quantidade || 0), 0);

  return (
    <CartContext.Provider
      value={{ 
        cart, 
        addToCart, 
        removeFromCart, 
        updateQuantity, // ✅ Exportando a função
        clearCart, 
        cartCount 
      }}
    >
      {children}
    </CartContext.Provider>
  );
}

export const useCart = () => useContext(CartContext);