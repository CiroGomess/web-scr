"use client";

import { AppBar, Toolbar, Typography, Button } from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";
import { usePathname } from "next/navigation";

const titles: Record<string, string> = {
  "/upload": "Upload de Documento",
  "/consulta": "Consulta de Produtos",
};

export default function Header() {
  const pathname = usePathname();

  return (
    <AppBar
      position="static"
      elevation={0}
      sx={{
        backgroundColor: "#f0f0f0",
        borderBottom: "1px solid #e5e7eb",
      }}
    >
      <Toolbar sx={{ justifyContent: "space-between" }}>
        <Typography variant="h6" color="text.primary">
          {titles[pathname] || "Dashboard"}
        </Typography>

        <Button
          variant="outlined"
          color="error"
          startIcon={<LogoutIcon />}
        >
          Sair
        </Button>
      </Toolbar>
    </AppBar>
  );
}
