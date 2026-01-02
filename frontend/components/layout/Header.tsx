"use client";

import { useRouter, usePathname } from "next/navigation";
import { AppBar, Toolbar, Typography, Button, Box, IconButton, Badge } from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";
import NotificationsIcon from "@mui/icons-material/Notifications";
import ShoppingCartIcon from "@mui/icons-material/ShoppingCart"; // Ícone novo
import { useCart } from "../../contexts/CartContext"; // Importe o hook

const brandColor = "#3731A0";

export default function Header() {
  const router = useRouter();
  const pathname = usePathname();
  const { cartCount } = useCart(); // Pegamos a contagem do contexto

  const getPageTitle = (path: string) => {
    switch (path) {
      case "/upload": return { title: "Upload de Arquivos", subtitle: "Gerenciamento" };
      case "/consulta": return { title: "Consulta de Produtos", subtitle: "Análises" };
      case "/carrinho": return { title: "Meu Carrinho", subtitle: "Finalizar Pedido" }; // Nova rota
      default: return { title: "Visão Geral", subtitle: "Dashboard" };
    }
  };

  const { title, subtitle } = getPageTitle(pathname);

  const handleLogout = () => {
    if (typeof window !== "undefined") localStorage.removeItem("token");
    router.push("/login");
  };

  return (
    <AppBar position="sticky" elevation={0} sx={{ backgroundColor: brandColor, zIndex: (theme) => theme.zIndex.drawer + 1 }}>
      <Toolbar sx={{ justifyContent: "space-between", height: 64 }}>
        
        <Box>
          <Typography variant="subtitle2" sx={{ fontSize: '0.75rem', textTransform: 'uppercase', color: "rgba(255, 255, 255, 0.7)" }}>
            {subtitle}
          </Typography>
          <Typography variant="h6" sx={{ fontWeight: 700, color: "#ffffff", lineHeight: 1.2 }}>
            {title}
          </Typography>
        </Box>

        <Box display="flex" alignItems="center" gap={2}>
          
          {/* BOTÃO DO CARRINHO */}
          <IconButton onClick={() => router.push("/carrinho")} sx={{ color: "white" }}>
            <Badge badgeContent={cartCount} color="error">
              <ShoppingCartIcon />
            </Badge>
          </IconButton>

          <IconButton size="small" sx={{ color: "rgba(255, 255, 255, 0.8)" }}>
            <NotificationsIcon />
          </IconButton>

          <Button
            onClick={handleLogout}
            variant="outlined"
            size="small"
            startIcon={<LogoutIcon />}
            sx={{
              borderColor: "rgba(255, 255, 255, 0.3)",
              color: "#ffffff",
              "&:hover": { borderColor: "#ffffff", backgroundColor: "rgba(255, 255, 255, 0.1)" },
            }}
          >
            Sair
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}