import { Dialog, DialogTitle, IconButton, CircularProgress } from "@mui/material";
import { Close, ContentCopy, CheckCircle, ShoppingCartCheckout } from "@mui/icons-material";
import { useState } from "react";
import services from "../../services/service";

type CartItem = {
    uid: string;
    codigo: string;
    nome: string;
    imagem: string;
    fornecedor: string;
    preco: number;
    quantidade: number;
};

interface CheckoutModalProps {
    open: boolean;
    onClose: () => void;
    fornecedor: string;
    itens: CartItem[];
}

export default function CheckoutModal({ open, onClose, fornecedor, itens }: CheckoutModalProps) {
    const [copied, setCopied] = useState(false);

    // Mantivemos o estado apenas para mostrar o "Check" verde visualmente após o envio do lote
    const [itemStatus, setItemStatus] = useState<Record<string, "success" | "idle">>({});

    // Estado para controlar o loading do botão "Enviar Tudo"
    const [isSendingAll, setIsSendingAll] = useState(false);

    // Função para enviar TODOS os itens (botão grande no rodapé)
    const handleFinalizarTudo = async () => {
        setIsSendingAll(true);

        try {
            // 1. Monta o payload com a lista completa
            const payload = {
                fornecedor: fornecedor, 
                itens: itens.map(i => ({
                    codigo: i.codigo,
                    quantidade: i.quantidade
                }))
            };
          
            // 2. Envia para a rota de lote do Backend
            await services("/automacao/carrinho/lote", {
                method: "POST",
                data: payload, // ✅ Axios usa "data"
                headers: { "Content-Type": "application/json" },
            });


            // 3. Atualiza visualmente todos os itens para "sucesso" (Check verde)
            const novoStatus: any = {};
            itens.forEach(i => novoStatus[i.codigo] = "success");
            setItemStatus(novoStatus);

            // 4. Abre o carrinho do fornecedor em nova aba
            // Pequeno delay para o usuário ver os checks verdes


        } catch (error) {
            console.error("Erro ao enviar lote:", error);
            alert("Houve um erro ao enviar os dados para o robô. Tente novamente.");
        } finally {
            setIsSendingAll(false);
        }
    };

    const copyToClipboard = () => {
        const text = itens.map(i => `${i.codigo}\t${i.quantidade}`).join("\n");
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const total = itens.reduce((acc, i) => acc + (i.preco * i.quantidade), 0);

    return (
        <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
            <div className="p-6">
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <DialogTitle className="p-0 text-xl font-bold text-gray-800">
                            Automação de Pedido: {fornecedor}
                        </DialogTitle>
                        <p className="text-sm text-gray-500 mt-1">
                            Confira os itens abaixo e clique em enviar para processar o lote no robô.
                        </p>
                    </div>
                    <IconButton onClick={onClose} size="small">
                        <Close />
                    </IconButton>
                </div>

                <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4 mb-6 flex justify-between items-center">
                    <div>
                        <p className="text-sm font-bold text-indigo-900">Resumo do Pedido</p>
                        <p className="text-xs text-indigo-700">{itens.length} itens • Total: {new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(total)}</p>
                    </div>
                    <button
                        onClick={copyToClipboard}
                        className="flex items-center gap-2 px-3 py-1.5 bg-white border border-indigo-200 text-indigo-700 rounded text-xs font-bold hover:bg-indigo-50 transition"
                    >
                        {copied ? <CheckCircle fontSize="small" className="text-green-500" /> : <ContentCopy fontSize="small" />}
                        {copied ? "Copiado!" : "Copiar Lista"}
                    </button>
                </div>

                <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-2">
                    {itens.map((item, idx) => (
                        <div key={idx} className="flex items-center gap-4 p-3 border border-gray-100 rounded-lg hover:shadow-sm transition bg-white">
                            <img src={item.imagem} alt={item.nome} className="w-12 h-12 object-contain" />

                            <div className="flex-1">
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-bold bg-gray-100 text-gray-600 px-1.5 rounded">{item.codigo}</span>
                                    <span className="text-xs text-gray-400">Qtd: {item.quantidade}</span>
                                </div>
                                <p className="text-sm font-medium text-gray-800 line-clamp-1">{item.nome}</p>
                            </div>

                            {/* Só exibe o selo de "Enviado" se o processo de lote já terminou para dar feedback visual */}
                            {itemStatus[item.codigo] === "success" && (
                                <div className="flex items-center gap-1 px-3 py-1 bg-green-100 text-green-700 text-xs font-bold rounded border border-green-200">
                                    <CheckCircle style={{ fontSize: 16 }} /> Enviado
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                <div className="mt-6 pt-4 border-t border-gray-100 text-right">
                    <p className="text-xs text-gray-500 mb-2">
                        Ao clicar abaixo, enviaremos todos os itens para o robô e abriremos o carrinho.
                    </p>

                    {/* BOTÃO ÚNICO DE AÇÃO */}
                    <button
                        onClick={handleFinalizarTudo}
                        disabled={isSendingAll}
                        className={`inline-flex items-center justify-center gap-2 px-6 py-3 text-white font-bold rounded-lg shadow-lg transition
                            ${isSendingAll
                                ? "bg-gray-400 cursor-not-allowed"
                                : "bg-emerald-600 hover:bg-emerald-700 hover:shadow-emerald-200"
                            }
                        `}
                    >
                        {isSendingAll ? (
                            <>
                                <CircularProgress size={20} color="inherit" />
                                Processando Robô...
                            </>
                        ) : (
                            <>
                                <ShoppingCartCheckout />
                                Enviar Tudo e Ir para Pagamento
                            </>
                        )}
                    </button>
                </div>
            </div>
        </Dialog>
    );
}