import { useCourses, useCreateCourse } from "@/hooks/use-courses";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { insertCourseSchema, type InsertCourse } from "@shared/schema";
import { Link } from "wouter";
import { 
  Plus, 
  Loader2, 
  Book, 
  MoreVertical, 
  Trash2, 
  Edit 
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { 
  Dialog, 
  DialogContent, 
  DialogHeader, 
  DialogTitle, 
  DialogTrigger,
  DialogDescription,
  DialogFooter
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useState } from "react";
import { useToast } from "@/hooks/use-toast";
import { format } from "date-fns";

export default function CoursesPage() {
  const { data: courses, isLoading } = useCourses();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const { toast } = useToast();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <Loader2 className="w-8 h-8 animate-spin text-primary/50" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-4xl font-serif font-bold text-primary mb-2">My Curriculum</h1>
          <p className="text-muted-foreground">Manage your courses and study materials.</p>
        </div>
        <CreateCourseDialog open={isCreateOpen} onOpenChange={setIsCreateOpen} />
      </div>

      {!courses?.length ? (
        <div className="flex flex-col items-center justify-center py-20 border-2 border-dashed border-border rounded-xl bg-secondary/10">
          <div className="p-4 bg-secondary rounded-full mb-4">
            <Book className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-medium text-foreground">No courses yet</h3>
          <p className="text-muted-foreground text-center max-w-sm mt-2 mb-6">
            Start your academic journey by creating your first course.
          </p>
          <Button onClick={() => setIsCreateOpen(true)} variant="outline">
            Create Course
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {courses.map((course) => (
            <Link key={course.id} href={`/courses/${course.id}`} className="block group">
              <div className="h-full bg-card hover:bg-card/50 border border-border/50 hover:border-primary/30 rounded-lg p-6 transition-all duration-300 shadow-sm hover:shadow-md hover:-translate-y-1 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
                  <div className="bg-background/80 backdrop-blur rounded-full p-1 border border-border">
                     <Edit className="w-4 h-4 text-muted-foreground" />
                  </div>
                </div>
                
                <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                  <span className="font-serif font-bold text-xl text-primary">
                    {course.title.charAt(0)}
                  </span>
                </div>
                
                <h3 className="font-serif font-bold text-xl mb-2 line-clamp-1 group-hover:text-primary transition-colors">
                  {course.title}
                </h3>
                <p className="text-muted-foreground text-sm line-clamp-2 mb-4 h-10">
                  {course.description}
                </p>
                
                <div className="flex items-center text-xs text-muted-foreground/80 pt-4 border-t border-border/30">
                  <span>Created {course.createdAt && format(new Date(course.createdAt), 'MMM d, yyyy')}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function CreateCourseDialog({ open, onOpenChange }: { open: boolean, onOpenChange: (o: boolean) => void }) {
  const { mutate, isPending } = useCreateCourse();
  const { toast } = useToast();
  
  const form = useForm<InsertCourse>({
    resolver: zodResolver(insertCourseSchema),
    defaultValues: {
      title: "",
      description: "",
      coverImageUrl: "",
    },
  });

  const onSubmit = (data: InsertCourse) => {
    mutate(data, {
      onSuccess: () => {
        onOpenChange(false);
        form.reset();
        toast({
          title: "Course Created",
          description: "Your new course has been added to the library.",
        });
      },
      onError: () => {
        toast({
          title: "Error",
          description: "Failed to create course. Please try again.",
          variant: "destructive",
        });
      }
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button className="gap-2 shadow-lg shadow-primary/20">
          <Plus className="w-4 h-4" /> New Course
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px] font-sans">
        <DialogHeader>
          <DialogTitle className="font-serif text-2xl">Create Course</DialogTitle>
          <DialogDescription>
            Add a new subject to your curriculum.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input id="title" placeholder="e.g. Philosophy 101" {...form.register("title")} />
            {form.formState.errors.title && (
              <p className="text-xs text-destructive">{form.formState.errors.title.message}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea 
              id="description" 
              placeholder="Brief overview of the course material..." 
              className="resize-none h-24"
              {...form.register("description")} 
            />
            {form.formState.errors.description && (
              <p className="text-xs text-destructive">{form.formState.errors.description.message}</p>
            )}
          </div>
          <DialogFooter>
            <Button type="submit" disabled={isPending}>
              {isPending ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : null}
              Create Course
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
