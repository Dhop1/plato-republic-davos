import { useCourse, useDocuments, useCreateDocument, useDeleteDocument } from "@/hooks/use-courses";
import { useParams, Link } from "wouter";
import { Loader2, FileText, ArrowLeft, Upload, Trash2, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState, useRef } from "react";
import { useToast } from "@/hooks/use-toast";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogDescription,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export default function CourseDetailPage() {
  const { id } = useParams();
  const courseId = Number(id);
  const { data: course, isLoading: isCourseLoading } = useCourse(courseId);
  const { data: documents, isLoading: isDocsLoading } = useDocuments(courseId);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  if (isCourseLoading || isDocsLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary/50" />
      </div>
    );
  }

  if (!course) {
    return (
      <div className="flex flex-col items-center justify-center h-[60vh] gap-4">
        <h2 className="text-2xl font-serif">Course Not Found</h2>
        <Link href="/">
          <Button variant="outline">
            <ArrowLeft className="w-4 h-4 mr-2" />
            Back to Library
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div>
        <Link href="/" className="inline-flex items-center text-sm text-muted-foreground hover:text-primary mb-4 transition-colors">
          <ArrowLeft className="w-4 h-4 mr-1" />
          Back to Library
        </Link>
        <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 border-b border-border/40 pb-6">
          <div className="max-w-3xl">
            <h1 className="text-4xl md:text-5xl font-serif font-bold text-primary mb-4">{course.title}</h1>
            <p className="text-lg text-muted-foreground leading-relaxed">{course.description}</p>
          </div>
          <AddDocumentDialog courseId={courseId} open={isUploadOpen} onOpenChange={setIsUploadOpen} />
        </div>
      </div>

      {/* Documents Grid */}
      <div className="space-y-4">
        <h2 className="text-2xl font-serif font-semibold flex items-center gap-2">
          <FileText className="w-6 h-6 text-accent" />
          Course Materials
        </h2>
        
        {!documents?.length ? (
          <div className="bg-secondary/20 border border-dashed border-border rounded-xl p-12 flex flex-col items-center justify-center text-center">
            <div className="p-4 bg-background rounded-full mb-4 shadow-sm">
              <Upload className="w-6 h-6 text-muted-foreground" />
            </div>
            <h3 className="font-medium text-lg mb-1">No documents uploaded</h3>
            <p className="text-muted-foreground text-sm max-w-xs mb-6">
              Upload text materials to this course to help the AI tutor understand the context.
            </p>
            <Button variant="outline" onClick={() => setIsUploadOpen(true)}>
              Upload Document
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {documents.map((doc) => (
              <DocumentCard key={doc.id} doc={doc} courseId={courseId} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function DocumentCard({ doc, courseId }: { doc: any, courseId: number }) {
  const { mutate: deleteDoc, isPending } = useDeleteDocument();
  const { toast } = useToast();

  const handleDelete = () => {
    if (confirm("Are you sure you want to delete this document?")) {
      deleteDoc({ id: doc.id, courseId }, {
        onSuccess: () => {
          toast({ title: "Deleted", description: "Document removed successfully." });
        },
        onError: () => {
          toast({ title: "Error", description: "Failed to delete document.", variant: "destructive" });
        }
      });
    }
  };

  return (
    <div className="group bg-card border border-border/50 p-4 rounded-lg hover:shadow-md transition-all duration-200 flex items-start gap-4">
      <div className="p-3 bg-secondary/50 rounded-md">
        <FileText className="w-5 h-5 text-primary" />
      </div>
      <div className="flex-1 min-w-0">
        <h4 className="font-medium truncate pr-2">{doc.title}</h4>
        <p className="text-xs text-muted-foreground mt-1 line-clamp-2 font-mono bg-secondary/30 p-1 rounded">
          {doc.content.substring(0, 100)}...
        </p>
      </div>
      <Button 
        variant="ghost" 
        size="icon" 
        className="opacity-0 group-hover:opacity-100 transition-opacity text-destructive hover:bg-destructive/10"
        onClick={handleDelete}
        disabled={isPending}
      >
        <Trash2 className="w-4 h-4" />
      </Button>
    </div>
  );
}

function AddDocumentDialog({ courseId, open, onOpenChange }: { courseId: number, open: boolean, onOpenChange: (o: boolean) => void }) {
  const { mutate, isPending } = useCreateDocument();
  const { toast } = useToast();
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setTitle(selectedFile.name.replace(/\.[^/.]+$/, "")); // Remove extension
      const text = await selectedFile.text();
      setContent(text);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title || !content) return;

    mutate({ courseId, title, content }, {
      onSuccess: () => {
        onOpenChange(false);
        setTitle("");
        setContent("");
        setFile(null);
        toast({ title: "Success", description: "Document added to course." });
      },
      onError: () => {
        toast({ title: "Error", description: "Failed to add document.", variant: "destructive" });
      }
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="gap-2 shadow-lg shadow-primary/20">
          <Upload className="w-4 h-4" /> Add Material
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[500px]">
        <DialogHeader>
          <DialogTitle className="font-serif text-2xl">Add Study Material</DialogTitle>
          <DialogDescription>
            Upload a text file or paste content directly.
          </DialogDescription>
        </DialogHeader>
        
        <form onSubmit={handleSubmit} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="file-upload">Upload File (.txt, .md)</Label>
            <div className="border-2 border-dashed border-border rounded-lg p-6 text-center hover:bg-secondary/10 transition-colors cursor-pointer relative">
              <input 
                id="file-upload" 
                type="file" 
                accept=".txt,.md,.json" 
                onChange={handleFileChange}
                className="absolute inset-0 opacity-0 cursor-pointer"
              />
              <div className="flex flex-col items-center gap-2">
                <Upload className="w-6 h-6 text-muted-foreground" />
                <span className="text-sm text-muted-foreground">
                  {file ? file.name : "Click or drag file to upload"}
                </span>
              </div>
            </div>
          </div>

          <div className="relative flex items-center py-2">
            <div className="flex-grow border-t border-border"></div>
            <span className="flex-shrink-0 mx-4 text-muted-foreground text-xs uppercase">Or enter manually</span>
            <div className="flex-grow border-t border-border"></div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="doc-title">Title</Label>
            <Input 
              id="doc-title" 
              value={title} 
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Document Title" 
              required
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="doc-content">Content</Label>
            <Textarea 
              id="doc-content" 
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Paste text content here..." 
              className="h-32 font-mono text-sm"
              required
            />
          </div>

          <div className="flex justify-end pt-4">
            <Button type="submit" disabled={isPending || !title || !content}>
              {isPending && <Loader2 className="w-4 h-4 animate-spin mr-2" />}
              Save Document
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
