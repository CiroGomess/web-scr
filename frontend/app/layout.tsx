import DashboardLayout from "@/components/layout/DashboardLayout";
import { CartProvider } from "../contexts/CartContext"; // 🟢 Importe o Provider aqui
import "./globals.css";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>
        {/* Envolvemos tudo com o CartProvider. 
          Assim, tanto o Header (que está dentro do DashboardLayout) 
          quanto as páginas (children) terão acesso ao carrinho.
        */}
        <CartProvider>
          <DashboardLayout>{children}</DashboardLayout>
        </CartProvider>
      </body>
    </html>
  );
}