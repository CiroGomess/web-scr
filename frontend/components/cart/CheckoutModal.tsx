"use client";

import { Dialog, DialogTitle, IconButton, CircularProgress } from "@mui/material";
import { Close, ContentCopy, CheckCircle, ShoppingCartCheckout } from "@mui/icons-material";
import { useEffect, useState } from "react";
import services from "../../services/service";

import FullScreenProcessingOverlay from "../layout/FullScreenProcessingOverlay";

// ✅ Ajuste do tipo para suportar UF/região e campos opcionais
type CartItem = {
  uid: string;
  codigo: string;
  nome: string;
  imagem: string;
  fornecedor: string;
  preco: number;
  quantidade: number;

  // NOVOS (opcionais)
  uf?: string; // ex: "SP"
  origem?: "REGIAO" | "OFERTA_GERAL" | string;

  preco_original?: number;
  teve_desconto?: boolean;
};

interface CheckoutModalProps {
  open: boolean;
  onClose: () => void;
  fornecedor: string;
  itens: CartItem[];
}

export default function CheckoutModal({ open, onClose, fornecedor, itens }: CheckoutModalProps) {
  const [copied, setCopied] = useState(false);
  const [itemStatus, setItemStatus] = useState<Record<string, "success" | "idle">>({});
  const [isSendingAll, setIsSendingAll] = useState(false);

  // Overlay fullscreen
  const [blocking, setBlocking] = useState(false);
  const [blockingMsg, setBlockingMsg] = useState("Enviando itens para o robô, aguarde...");

  // Bloqueia fechar aba/refresh durante o processamento
  useEffect(() => {
    if (!blocking) return;

    const beforeUnloadHandler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("beforeunload", beforeUnloadHandler);

    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("beforeunload", beforeUnloadHandler);
    };
  }, [blocking]);

  const handleFinalizarTudo = async () => {
    if (isSendingAll) return;

    setIsSendingAll(true);
    setBlocking(true);
    setBlockingMsg("Enviando itens para o robô, aguarde...");

    try {
      const payload = {
        fornecedor: fornecedor,
        itens: itens.map((i) => ({
          codigo: i.codigo,
          quantidade: i.quantidade,

          // ✅ envia UF se existir (backend pode ignorar se não usa)
          uf: i.uf || undefined,
        })),
      };

      const result = await services("/automacao/carrinho/lote", {
        method: "POST",
        data: payload,
        headers: { "Content-Type": "application/json" },
      });

      if (result?.success === false) {
        throw new Error(result?.data?.message || "Falha ao enviar o lote para o robô");
      }

      // ✅ Marca todos como enviados (melhor chave: uid, pq código pode repetir em UF diferente)
      const novoStatus: Record<string, "success" | "idle"> = {};
      itens.forEach((i) => (novoStatus[i.uid] = "success"));
      setItemStatus(novoStatus);

      setBlockingMsg("Lote enviado com sucesso! Abrindo carrinho...");

      setTimeout(() => {
        setBlocking(false);
      }, 900);
    } catch (error: any) {
      console.error("Erro ao enviar lote:", error);
      setBlockingMsg("Ocorreu um erro ao enviar para o robô.");

      setTimeout(() => {
        setBlocking(false);
      }, 1200);

      alert(error?.message || "Houve um erro ao enviar os dados para o robô. Tente novamente.");
    } finally {
      setIsSendingAll(false);
    }
  };

  const copyToClipboard = () => {
    // ✅ Inclui UF na cópia quando existir
    const text = itens
      .map((i) => {
        const uf = i.uf ? `\t${i.uf}` : "";
        return `${i.codigo}\t${i.quantidade}${uf}`;
      })
      .join("\n");

    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const total = itens.reduce((acc, i) => acc + i.preco * i.quantidade, 0);

  // Importante: bloqueia o close do Dialog enquanto estiver rodando
  const handleCloseSafe = () => {
    if (blocking || isSendingAll) return;
    onClose();
  };

  return (
    <>
      <FullScreenProcessingOverlay open={blocking} title="Processamento em andamento" message={blockingMsg} />

      <Dialog open={open} onClose={handleCloseSafe} maxWidth="md" fullWidth>
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

            <IconButton onClick={handleCloseSafe} size="small" disabled={blocking || isSendingAll}>
              <Close />
            </IconButton>
          </div>

          <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-4 mb-6 flex justify-between items-center">
            <div>
              <p className="text-sm font-bold text-indigo-900">Resumo do Pedido</p>
              <p className="text-xs text-indigo-700">
                {itens.length} itens • Total:{" "}
                {new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(total)}
              </p>

              {/* ✅ Mostra um resumo de UFs presentes */}
              {(() => {
                const ufs = Array.from(new Set(itens.map((i) => i.uf).filter(Boolean))) as string[];
                if (ufs.length === 0) return null;
                return (
                  <p className="text-xs text-indigo-700 mt-1">
                    UFs no lote: <span className="font-bold">{ufs.join(", ")}</span>
                  </p>
                );
              })()}
            </div>

            <button
              onClick={copyToClipboard}
              disabled={blocking || isSendingAll}
              className="flex items-center gap-2 px-3 py-1.5 bg-white border border-indigo-200 text-indigo-700 rounded text-xs font-bold hover:bg-indigo-50 transition disabled:opacity-60"
            >
              {copied ? <CheckCircle fontSize="small" className="text-green-500" /> : <ContentCopy fontSize="small" />}
              {copied ? "Copiado!" : "Copiar Lista"}
            </button>
          </div>

          <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-2">
            {itens.map((item) => (
              <div
                key={item.uid}
                className="flex items-center gap-4 p-3 border border-gray-100 rounded-lg hover:shadow-sm transition bg-white"
              >
                <img src={item.imagem} alt={item.nome} className="w-12 h-12 object-contain" />

                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold bg-gray-100 text-gray-600 px-1.5 rounded">
                      {item.codigo}
                    </span>

                    <span className="text-xs text-gray-400">Qtd: {item.quantidade}</span>

                    {/* ✅ Mostra UF quando existir */}
                    {item.uf && (
                      <span className="text-[11px] font-bold bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full">
                        UF: {item.uf}
                      </span>
                    )}
                  </div>

                  <p className="text-sm font-medium text-gray-800 line-clamp-1">{item.nome}</p>
                </div>

                {/* ✅ Status por UID (evita conflito se repetir código com UF diferente) */}
                {itemStatus[item.uid] === "success" && (
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

            <button
              onClick={handleFinalizarTudo}
              disabled={isSendingAll || blocking}
              className={`inline-flex items-center justify-center gap-2 px-6 py-3 text-white font-bold rounded-lg shadow-lg transition
                ${
                  isSendingAll || blocking
                    ? "bg-gray-400 cursor-not-allowed"
                    : "bg-emerald-600 hover:bg-emerald-700 hover:shadow-emerald-200"
                }`}
            >
              {isSendingAll || blocking ? (
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
    </>
  );
}
