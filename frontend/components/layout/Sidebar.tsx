"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    Drawer,
    Toolbar,
    List,
    ListItemButton,
    ListItemIcon,
    ListItemText,
    Typography,
    Box,
} from "@mui/material";

import UploadFileIcon from "@mui/icons-material/UploadFile";
import SearchIcon from "@mui/icons-material/Search";
import Inventory2Icon from "@mui/icons-material/Inventory2";

const drawerWidth = 270;

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
];

export default function Sidebar() {
    const pathname = usePathname();

    return (
        <Drawer
            variant="permanent"
            sx={{
                width: drawerWidth,
                [`& .MuiDrawer-paper`]: {
                    width: drawerWidth,
                    backgroundColor: "#ffffff", // exemplo: slate corporativo
                    color: "#444444",
                    borderRight: "1px solid #e5e7eb",
                },
            }}
        >
            <Toolbar>
                <Box display="flex" alignItems="center" gap={1}>
                    <Inventory2Icon color="primary" />
                    <Typography variant="h6">Produtos</Typography>
                </Box>
            </Toolbar>

            <List sx={{ px: 1 }}>
                {menuItems.map((item) => {
                    const active = pathname === item.href;

                    return (
                        <ListItemButton
                            key={item.href}
                            component={Link}
                            href={item.href}
                            sx={{
                                borderRadius: 2,
                                mb: 0.5,
                                backgroundColor: active ? "primary.main" : "transparent",
                                color: active ? "#fff" : "inherit",
                                "&:hover": {
                                    backgroundColor: active
                                        ? "primary.dark"
                                        : "rgba(0,0,0,0.04)",
                                },
                            }}
                        >
                            <ListItemIcon
                                sx={{ color: active ? "#fff" : "text.secondary" }}
                            >
                                {item.icon}
                            </ListItemIcon>
                            <ListItemText primary={item.label} />
                        </ListItemButton>
                    );
                })}
            </List>
        </Drawer>
    );
}
