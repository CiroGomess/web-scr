"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";

// Definição do item do carrinho
type CartItem = {
  uid: string; // ID único (codigo + fornecedor) para diferenciar ofertas
  codigo: string;
  nome: string;
  imagem: string;
  fornecedor: string;
  preco: number;
  quantidade: number;
};

type CartContextType = {
  cart: CartItem[];
  addToCart: (item: CartItem) => void;
  removeFromCart: (uid: string) => void;
  clearCart: () => void;
  cartCount: number;
};

const CartContext = createContext<CartContextType>({} as CartContextType);

export function CartProvider({ children }: { children: ReactNode }) {
  const [cart, setCart] = useState<CartItem[]>([]);

  // Carregar do LocalStorage ao iniciar
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedCart = localStorage.getItem("carrinho_compras");
      if (savedCart) {
        setCart(JSON.parse(savedCart));
      }
    }
  }, []);

  // Salvar no LocalStorage sempre que mudar
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("carrinho_compras", JSON.stringify(cart));
    }
  }, [cart]);

  const addToCart = (newItem: CartItem) => {
    setCart((prev) => {
      // Verifica se o item já existe (mesmo produto E mesmo fornecedor)
      const exists = prev.find((item) => item.uid === newItem.uid);
      if (exists) {
        return prev.map((item) =>
          item.uid === newItem.uid
            ? { ...item, quantidade: item.quantidade + 1 }
            : item
        );
      }
      return [...prev, newItem];
    });
  };

  const removeFromCart = (uid: string) => {
    setCart((prev) => prev.filter((item) => item.uid !== uid));
  };

  const clearCart = () => {
    setCart([]);
  };

  const cartCount = cart.reduce((acc, item) => acc + item.quantidade, 0);

  return (
    <CartContext.Provider value={{ cart, addToCart, removeFromCart, clearCart, cartCount }}>
      {children}
    </CartContext.Provider>
  );
}

export const useCart = () => useContext(CartContext);