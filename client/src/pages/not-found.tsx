import { Link } from "wouter";
import { Card, CardContent } from "@/components/ui/card";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background paper-texture p-4">
      <Card className="w-full max-w-md mx-auto border-border bg-card/80 backdrop-blur shadow-xl">
        <CardContent className="pt-6 text-center space-y-6">
          <div className="flex justify-center">
            <AlertCircle className="h-16 w-16 text-destructive/80" />
          </div>
          
          <div className="space-y-2">
            <h1 className="text-3xl font-serif font-bold text-foreground">404 Not Found</h1>
            <p className="text-muted-foreground font-sans">
              "The knowledge you seek is not in this archive."
            </p>
          </div>

          <Link href="/">
            <Button className="w-full shadow-lg">
              Return to the Library
            </Button>
          </Link>
        </CardContent>
      </Card>
    </div>
  );
}
