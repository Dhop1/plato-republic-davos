import { Link, useLocation } from "wouter";
import { useAuth } from "@/hooks/use-auth";
import { 
  BookOpen, 
  MessageSquare, 
  LogOut, 
  User, 
  Menu,
  X,
  Plus
} from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";

export function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const { user, logout } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navigation = [
    { name: "Courses", href: "/", icon: BookOpen },
    { name: "Tutor Chat", href: "/chat", icon: MessageSquare },
  ];

  const isActive = (path: string) => location === path;

  return (
    <div className="min-h-screen bg-background text-foreground flex font-sans paper-texture">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex flex-col w-64 border-r border-border/50 bg-background/50 backdrop-blur-sm fixed h-full z-10">
        <div className="p-6 border-b border-border/30">
          <h1 className="text-2xl font-bold font-serif text-primary tracking-tight">
            The Republic
          </h1>
          <p className="text-xs text-muted-foreground mt-1 uppercase tracking-widest">
            School of Thought
          </p>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {navigation.map((item) => {
            const active = isActive(item.href);
            return (
              <Link key={item.name} href={item.href} className={`
                flex items-center gap-3 px-4 py-3 rounded-md transition-all duration-200 group
                ${active 
                  ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20 font-medium" 
                  : "text-muted-foreground hover:bg-secondary hover:text-secondary-foreground"
                }
              `}>
                <item.icon className={`w-5 h-5 ${active ? "text-primary-foreground" : "text-muted-foreground group-hover:text-primary"}`} />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-border/30 bg-secondary/20">
          <div className="flex items-center gap-3 mb-4 px-2">
            <Avatar className="h-9 w-9 border border-border">
              <AvatarImage src={user?.profileImageUrl || undefined} />
              <AvatarFallback className="bg-primary/10 text-primary">
                {user?.firstName?.[0]}{user?.lastName?.[0]}
              </AvatarFallback>
            </Avatar>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {user?.firstName} {user?.lastName}
              </p>
              <p className="text-xs text-muted-foreground truncate">
                Scholar
              </p>
            </div>
          </div>
          <Button 
            variant="ghost" 
            className="w-full justify-start text-muted-foreground hover:text-destructive hover:bg-destructive/10"
            onClick={() => logout()}
          >
            <LogOut className="w-4 h-4 mr-2" />
            Sign Out
          </Button>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="lg:hidden fixed top-0 w-full z-20 bg-background/80 backdrop-blur-md border-b border-border p-4 flex items-center justify-between">
        <h1 className="text-xl font-bold font-serif text-primary">The Republic</h1>
        <Sheet open={isMobileMenuOpen} onOpenChange={setIsMobileMenuOpen}>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon">
              <Menu className="w-5 h-5" />
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-64 p-0">
            <div className="p-6 border-b border-border/30">
              <h1 className="text-2xl font-bold font-serif text-primary">The Republic</h1>
            </div>
            <nav className="flex-1 p-4 space-y-2">
              {navigation.map((item) => (
                <Link key={item.name} href={item.href} onClick={() => setIsMobileMenuOpen(false)} className={`
                  flex items-center gap-3 px-4 py-3 rounded-md transition-all
                  ${isActive(item.href) 
                    ? "bg-primary text-primary-foreground" 
                    : "text-muted-foreground hover:bg-secondary"
                  }
                `}>
                  <item.icon className="w-5 h-5" />
                  {item.name}
                </Link>
              ))}
            </nav>
            <div className="absolute bottom-0 w-full p-4 border-t border-border/30">
              <Button 
                variant="ghost" 
                className="w-full justify-start text-muted-foreground hover:text-destructive"
                onClick={() => logout()}
              >
                <LogOut className="w-4 h-4 mr-2" />
                Sign Out
              </Button>
            </div>
          </SheetContent>
        </Sheet>
      </div>

      {/* Main Content Area */}
      <main className="flex-1 lg:pl-64 min-h-screen pt-16 lg:pt-0">
        <div className="max-w-5xl mx-auto p-4 md:p-8 lg:p-12 animate-in fade-in duration-500">
          {children}
        </div>
      </main>
    </div>
  );
}
