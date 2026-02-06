import { useState, useRef, useEffect } from "react";
import { useConversations, useConversation, useCreateConversation, useDeleteConversation, type Message } from "@/hooks/use-chat";
import { useAuth } from "@/hooks/use-auth";
import { Send, Plus, MessageSquare, Trash2, Bot, User as UserIcon, Loader2, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

export default function ChatPage() {
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const { data: conversations, isLoading: isConvosLoading } = useConversations();
  const { mutate: createConvo } = useCreateConversation();

  const handleCreate = () => {
    createConvo(`Session ${new Date().toLocaleDateString()}`, {
      onSuccess: (data) => setSelectedId(data.id),
    });
  };

  useEffect(() => {
    if (conversations?.length && !selectedId) {
      setSelectedId(conversations[0].id);
    }
  }, [conversations, selectedId]);

  return (
    <div className="h-[calc(100vh-4rem)] lg:h-[calc(100vh-2rem)] flex gap-6 overflow-hidden">
      {/* Sidebar List */}
      <div className="w-64 flex-shrink-0 flex flex-col bg-card border border-border/50 rounded-xl overflow-hidden shadow-sm hidden md:flex">
        <div className="p-4 border-b border-border/50">
          <Button onClick={handleCreate} className="w-full justify-start gap-2" variant="outline">
            <Plus className="w-4 h-4" /> New Session
          </Button>
        </div>
        <ScrollArea className="flex-1 p-2">
          {isConvosLoading ? (
            <div className="p-4 text-center text-sm text-muted-foreground">Loading history...</div>
          ) : (
            <div className="space-y-1">
              {conversations?.map((convo) => (
                <ConversationItem 
                  key={convo.id} 
                  convo={convo} 
                  isSelected={convo.id === selectedId} 
                  onSelect={() => setSelectedId(convo.id)} 
                />
              ))}
              {!conversations?.length && (
                <div className="p-4 text-center text-sm text-muted-foreground italic">
                  No previous sessions.
                </div>
              )}
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-card border border-border/50 rounded-xl overflow-hidden shadow-sm relative">
        {selectedId ? (
          <ChatInterface conversationId={selectedId} />
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center p-8 text-center bg-secondary/10">
            <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mb-4">
              <Sparkles className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-2xl font-serif font-bold text-primary mb-2">The Tutor is In</h2>
            <p className="text-muted-foreground max-w-sm">
              Select a conversation from the sidebar or start a new session to begin your dialogue.
            </p>
            <Button onClick={handleCreate} className="mt-6 md:hidden">
              Start New Session
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function ConversationItem({ convo, isSelected, onSelect }: { convo: any, isSelected: boolean, onSelect: () => void }) {
  const { mutate: deleteConvo } = useDeleteConversation();

  return (
    <div
      className={cn(
        "group flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors text-sm",
        isSelected ? "bg-primary/10 text-primary font-medium" : "hover:bg-secondary text-muted-foreground"
      )}
      onClick={onSelect}
    >
      <div className="flex items-center gap-3 overflow-hidden">
        <MessageSquare className="w-4 h-4 flex-shrink-0" />
        <span className="truncate">{convo.title}</span>
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          if(confirm("Delete this conversation?")) deleteConvo(convo.id);
        }}
        className={cn(
          "opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/10 hover:text-destructive rounded transition-all",
          isSelected && "opacity-100"
        )}
      >
        <Trash2 className="w-3 h-3" />
      </button>
    </div>
  );
}

function ChatInterface({ conversationId }: { conversationId: number }) {
  const { data: conversation, isLoading } = useConversation(conversationId);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();

  useEffect(() => {
    if (conversation?.messages) {
      setMessages(conversation.messages);
    }
  }, [conversation]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;

    const userMsg: Message = {
      id: Date.now(), // temp id
      role: "user",
      content: input,
      createdAt: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsStreaming(true);

    try {
      const res = await fetch(`/api/conversations/${conversationId}/messages`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: userMsg.content }),
      });

      if (!res.ok) throw new Error("Failed to send message");
      if (!res.body) throw new Error("No response body");

      // Setup SSE reader
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      
      const assistantMsg: Message = {
        id: Date.now() + 1,
        role: "assistant",
        content: "",
        createdAt: new Date().toISOString()
      };

      setMessages(prev => [...prev, assistantMsg]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const jsonStr = line.slice(6);
            if (!jsonStr) continue;
            try {
              const data = JSON.parse(jsonStr);
              if (data.done) {
                setIsStreaming(false);
                break;
              }
              if (data.content) {
                setMessages(prev => prev.map(msg => 
                  msg.id === assistantMsg.id 
                    ? { ...msg, content: msg.content + data.content }
                    : msg
                ));
              }
            } catch (e) {
              console.error("Failed to parse SSE chunk", e);
            }
          }
        }
      }
    } catch (error) {
      console.error(error);
      setIsStreaming(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary/30" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-[url('https://www.transparenttextures.com/patterns/cream-paper.png')]">
      {/* Chat Header */}
      <div className="p-4 border-b border-border/50 bg-background/80 backdrop-blur-sm z-10">
        <h3 className="font-serif font-bold text-lg">{conversation?.title}</h3>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6" ref={scrollRef}>
        {messages.map((msg, idx) => (
          <div 
            key={msg.id || idx} 
            className={cn(
              "flex gap-4 max-w-3xl mx-auto animate-in fade-in slide-in-from-bottom-2 duration-300",
              msg.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            {msg.role !== "user" && (
              <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20 flex-shrink-0 mt-1">
                <Bot className="w-5 h-5 text-primary" />
              </div>
            )}
            
            <div className={cn(
              "p-4 rounded-xl shadow-sm text-sm leading-relaxed",
              msg.role === "user" 
                ? "bg-primary text-primary-foreground rounded-tr-none" 
                : "bg-background border border-border rounded-tl-none font-mono text-foreground/90"
            )}>
              {msg.content}
            </div>

            {msg.role === "user" && (
               <Avatar className="w-8 h-8 border border-border mt-1">
                <AvatarImage src={user?.profileImageUrl || undefined} />
                <AvatarFallback className="bg-primary/10 text-primary">
                  <UserIcon className="w-4 h-4" />
                </AvatarFallback>
              </Avatar>
            )}
          </div>
        ))}
        {isStreaming && (
          <div className="flex gap-4 max-w-3xl mx-auto">
             <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center border border-primary/20 flex-shrink-0">
                <Bot className="w-5 h-5 text-primary" />
              </div>
              <div className="flex items-center gap-1 p-3">
                <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span className="w-2 h-2 bg-primary/40 rounded-full animate-bounce"></span>
              </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 bg-background/80 backdrop-blur-sm border-t border-border/50">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto relative flex items-center gap-2">
          <Input 
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask your question..."
            className="pr-12 h-12 rounded-full border-border/50 shadow-inner bg-background focus-visible:ring-primary/20 font-serif"
            disabled={isStreaming}
          />
          <Button 
            type="submit" 
            size="icon"
            disabled={!input.trim() || isStreaming}
            className="absolute right-1 w-10 h-10 rounded-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm"
          >
            {isStreaming ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </form>
        <p className="text-center text-xs text-muted-foreground mt-2 opacity-50">
          The tutor may produce inaccurate information. Always verify with primary texts.
        </p>
      </div>
    </div>
  );
}
