"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Box,
} from "@mui/material";

import UploadFileIcon from "@mui/icons-material/UploadFile";
import SearchIcon from "@mui/icons-material/Search";

import logo from "../../assets/logo.png";

const drawerWidth = 260; // Largura um pouco mais compacta e elegante

// Definição de cores baseada no seu #3731A0
const colors = {
  primary: "#3731A0",
  primaryLight: "#EEEDF9", // Um lilás bem clarinho para fundo do active
  text: "#475569", // Cinza profissional (Slate)
  textActive: "#3731A0",
};

const menuItems = [
  {
    label: "Upload Documento",
    icon: <UploadFileIcon />,
    href: "/upload",
  },
  {
    label: "Consulta Produtos",
    icon: <SearchIcon />,
    href: "/consulta",
  },
  // Exemplo de como adicionar mais itens futuramente
  // {
  //   label: "Dashboards",
  //   icon: <DashboardIcon />,
  //   href: "/dashboard",
  // },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        [`& .MuiDrawer-paper`]: {
          width: drawerWidth,
          boxSizing: "border-box",
          backgroundColor: "#ffffff",
          borderRight: "1px solid #E2E8F0", // Borda sutil
          boxShadow: "4px 0 24px rgba(0,0,0,0.02)", // Sombra muito leve na direita
        },
      }}
    >
   
      <Box
        sx={{
          height: 64,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          px: 3,
          borderBottom: "1px solid #F1F5F9",
          backgroundColor: "#ffffff",
        }}
      >
        <Box
          component="img"
          src={logo.src}
          alt="Logo"
          sx={{
            height: 44,      // ajuste aqui para maior/menor
            width: "auto",
            objectFit: "contain",
          }}
        />
      </Box>

      {/* --- MENU --- */}
      <Box sx={{ overflow: "auto", mt: 2, px: 2 }}>
        <List>
          {menuItems.map((item) => {
            const active = pathname === item.href;

            return (
              <ListItemButton
                key={item.href}
                component={Link}
                href={item.href}
                sx={{
                  mb: 1,
                  borderRadius: "8px", // Bordas arredondadas modernas
                  color: active ? colors.textActive : colors.text,
                  backgroundColor: active ? colors.primaryLight : "transparent",
                  transition: "all 0.2s ease-in-out",
                  position: "relative",
                  "&:hover": {
                    backgroundColor: active ? colors.primaryLight : "#F8FAFC",
                    transform: "translateX(4px)", // Pequeno movimento ao passar o mouse
                  },
                  // Barra lateral indicando ativo (opcional, mas chique)
                  "&::before": active
                    ? {
                      content: '""',
                      position: "absolute",
                      left: "-8px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      height: "20px",
                      width: "4px",
                      backgroundColor: colors.primary,
                      borderRadius: "0 4px 4px 0",
                    }
                    : {},
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 40,
                    color: active ? colors.primary : "#94A3B8", // Ícone cinza quando inativo, Roxo quando ativo
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{
                    fontSize: "0.95rem",
                    fontWeight: active ? 600 : 500,
                  }}
                />
              </ListItemButton>
            );
          })}
        </List>
      </Box>

      {/* --- RODAPÉ DA SIDEBAR (Opcional) --- */}
      <Box sx={{ mt: "auto", p: 2 }}>
        <Typography variant="caption" display="block" align="center" color="text.secondary">
          v1.0.0
        </Typography>
      </Box>
    </Drawer>
  );
}