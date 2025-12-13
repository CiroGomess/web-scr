"use client";

import { ReactNode } from "react";
import { ThemeProvider, CssBaseline, Box } from "@mui/material";
import { theme } from "@/theme/theme";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function DashboardLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />

      <Box sx={{ display: "flex", height: "100vh" }}>
        <Sidebar />

        <Box sx={{ flexGrow: 1, display: "flex", flexDirection: "column" }}>
          <Header />

          <Box
            component="main"
            sx={{
              flexGrow: 1,
              p: 4,
              backgroundColor: "background.default",
              overflow: "auto",
            }}
          >
            {children}
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
