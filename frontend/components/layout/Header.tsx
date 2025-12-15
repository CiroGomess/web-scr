"use client";

import { AppBar, Toolbar, Typography, Button } from "@mui/material";
import LogoutIcon from "@mui/icons-material/Logout";


export default function Header() {


  return (
    <AppBar
      position="static"
      elevation={0}
      sx={{
        backgroundColor: "#3731a0",
        borderBottom: "1px solid #e5e7eb",
        color: "#ffffff",
      }}
    >
      <Toolbar sx={{ justifyContent: "space-between" }}>
        <Typography variant="h6" color="text.primary">

        </Typography>

        <Button
          variant="contained"
          color="error"
          startIcon={<LogoutIcon />}
        >
          Sair
        </Button>
      </Toolbar>
    </AppBar>
  );
}
