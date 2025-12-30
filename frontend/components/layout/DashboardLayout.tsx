"use client"; // <--- 1. OBRIGATÓRIO: Transforma em Client Component

import { usePathname } from "next/navigation"; // <--- 2. Importar o hook de rota
import Sidebar from "./Sidebar"; // (Seus imports originais...)
import Header from "./Header";   // (Seus imports originais...)

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); // <--- 3. Pega a rota atual

  // 4. LÓGICA: Se for "/login", retorna SÓ o conteúdo (sem sidebar)
  if (pathname === "/login") {
    return <main className="min-h-screen bg-gray-100">{children}</main>;
  }

  // 5. Se NÃO for login, retorna o layout completo (Dashboard)
  return (
    <div className="flex h-screen bg-gray-100">
      {/* Sua Sidebar */}
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Seu Header */}
        <Header />

        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-50 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}