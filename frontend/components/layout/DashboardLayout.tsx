"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react"; // Importar Hooks
import Sidebar from "./Sidebar";
import Header from "./Header";
import { Box, CssBaseline, CircularProgress } from "@mui/material";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);

  // 1. LÓGICA DE PROTEÇÃO DE ROTA
  useEffect(() => {
    // Se for login, não precisa verificar token
    if (pathname === "/login") {
        setAuthorized(true);
        return;
    }

    // Tenta pegar o token do localStorage
    const token = localStorage.getItem("token");

    if (!token) {
        // Se não tem token, chuta para o login
        router.push("/login");
    } else {
        // Se tem token, libera o acesso
        setAuthorized(true);
    }
  }, [pathname, router]);

  // Enquanto verifica a autorização, pode mostrar nada ou um loading
  if (!authorized) {
      return null; // ou <div className="h-screen flex items-center justify-center"><CircularProgress /></div>
  }

  // 2. LAYOUT DE LOGIN (Tela Cheia)
  if (pathname === "/login") {
    return (
      <main className="min-h-screen bg-gray-950 flex flex-col">
        <CssBaseline />
        {children}
      </main>
    );
  }

  // 3. LAYOUT DO SISTEMA (Com Sidebar e Header)
  return (
    <Box sx={{ display: "flex", height: "100vh", overflow: "hidden", bgcolor: "#F8FAFC" }}>
      <CssBaseline />
      
      <Sidebar />

      <Box sx={{ flexGrow: 1, display: "flex", flexDirection: "column", height: "100%" }}>
        <Header />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            overflowY: "auto",
            overflowX: "hidden",
            backgroundColor: "#F8FAFC",
          }}
        >
          <Box sx={{ maxWidth: "1600px", mx: "auto", width: "100%" }}>
             {children}
          </Box>
        </Box>
      </Box>
    </Box>
  );
}