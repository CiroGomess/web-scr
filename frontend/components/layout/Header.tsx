"use client";

import { useRouter, usePathname } from "next/navigation";
import { AppBar, Toolbar, Typography, Button, Box, IconButton } from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";
import NotificationsIcon from "@mui/icons-material/Notifications";

// Definição das cores
const brandColor = "#3731A0";

export default function Header() {
  const router = useRouter(); // 1. Inicializa o roteador
  const pathname = usePathname();

  // Define o título baseado na rota
  const getPageTitle = (path: string) => {
    switch (path) {
      case "/upload":
        return { title: "Upload de Arquivos", subtitle: "Gerenciamento" };
      case "/consulta":
        return { title: "Consulta de Produtos", subtitle: "Análises" };
      default:
        return { title: "Visão Geral", subtitle: "Dashboard" };
    }
  };

  const { title, subtitle } = getPageTitle(pathname);

  // 2. Função que realiza o redirecionamento
  const handleLogout = () => {
    // 1. Limpa o token de autenticação
    if (typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("user_email"); // Limpa o email se estiver salvo
    }

    // 2. Redireciona para a tela de login
    router.push("/login");
  };

  return (
    <AppBar
      position="sticky"
      elevation={0}
      sx={{
        backgroundColor: brandColor,
        borderBottom: "1px solid rgba(255, 255, 255, 0.1)",
        color: "#ffffff",
        zIndex: (theme) => theme.zIndex.drawer + 1,
      }}
    >
      <Toolbar sx={{ justifyContent: "space-between", height: 64 }}>

        {/* Lado Esquerdo: Títulos */}
        <Box>
          <Typography
            variant="subtitle2"
            sx={{
              fontSize: '0.75rem',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              color: "rgba(255, 255, 255, 0.7)"
            }}
          >
            {subtitle}
          </Typography>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 700,
              color: "#ffffff",
              lineHeight: 1.2
            }}
          >
            {title}
          </Typography>
        </Box>

        {/* Lado Direito: Ações */}
        <Box display="flex" alignItems="center" gap={2}>

          <IconButton
            size="small"
            sx={{
              color: "rgba(255, 255, 255, 0.8)",
              "&:hover": { backgroundColor: "rgba(255, 255, 255, 0.1)" }
            }}
          >
            <NotificationsIcon />
          </IconButton>


          {/* 3. Botão com o evento onClick vinculado */}
          <Button
            onClick={handleLogout}
            variant="outlined"
            size="small"
            startIcon={<LogoutIcon />}
            sx={{
              borderColor: "rgba(255, 255, 255, 0.3)",
              color: "#ffffff",
              textTransform: "none",
              fontWeight: 600,
              borderRadius: "8px",
              paddingX: 2,
              "&:hover": {
                borderColor: "#ffffff",
                backgroundColor: "rgba(255, 255, 255, 0.1)",
              },
            }}
          >
            Sair
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}