import { Button } from "@/components/ui/button";
import { BookOpen } from "lucide-react";

export default function LoginPage() {
  const handleLogin = () => {
    window.location.href = "/api/login";
  };

  return (
    <div className="min-h-screen grid grid-cols-1 lg:grid-cols-2">
      {/* Left Panel - Art & Atmosphere */}
      <div className="hidden lg:flex flex-col justify-between p-12 bg-primary/95 text-primary-foreground relative overflow-hidden">
        {/* Abstract Pattern / Texture Overlay */}
        <div className="absolute inset-0 opacity-10 paper-texture pointer-events-none"></div>
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_var(--tw-gradient-stops))] from-accent/20 to-transparent pointer-events-none"></div>

        <div className="z-10">
          <div className="flex items-center gap-3 mb-8">
            <div className="p-2 bg-primary-foreground/10 rounded-lg backdrop-blur-sm">
              <BookOpen className="w-6 h-6" />
            </div>
            <span className="font-serif font-bold text-xl tracking-wide">The Republic</span>
          </div>
        </div>

        <div className="z-10 max-w-lg">
          <h1 className="font-serif text-5xl leading-tight mb-6">
            "The direction in which education starts a man will determine his future life."
          </h1>
          <p className="font-sans text-lg opacity-80 italic">
            — Plato, The Republic
          </p>
        </div>

        <div className="z-10 text-sm opacity-60">
          © {new Date().getFullYear()} The Republic Institute
        </div>
      </div>

      {/* Right Panel - Login Action */}
      <div className="flex flex-col justify-center items-center p-8 bg-background paper-texture relative">
        <div className="w-full max-w-md space-y-8">
          <div className="text-center lg:text-left">
            <div className="lg:hidden flex justify-center mb-6">
              <div className="p-3 bg-primary/5 rounded-full">
                <BookOpen className="w-8 h-8 text-primary" />
              </div>
            </div>
            <h2 className="text-3xl font-serif font-bold text-foreground">Welcome, Scholar</h2>
            <p className="mt-2 text-muted-foreground">
              Sign in to access your curriculum and consult with the AI Tutor.
            </p>
          </div>

          <div className="space-y-4 pt-4">
            <Button 
              onClick={handleLogin}
              className="w-full h-12 text-base font-medium shadow-lg hover:shadow-xl transition-all duration-300 bg-primary hover:bg-primary/90 text-primary-foreground"
            >
              Continue with Replit Identity
            </Button>
            
            <p className="text-xs text-center text-muted-foreground mt-4">
              By entering, you agree to our academic code of conduct.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
