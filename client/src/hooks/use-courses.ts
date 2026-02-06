import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, buildUrl, type CreateCourseRequest, type UpdateCourseRequest, type CreateDocumentRequest } from "@shared/routes";
import { z } from "zod";

// ============================================
// COURSES HOOKS
// ============================================

export function useCourses() {
  return useQuery({
    queryKey: [api.courses.list.path],
    queryFn: async () => {
      const res = await fetch(api.courses.list.path, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch courses");
      const data = await res.json();
      return api.courses.list.responses[200].parse(data);
    },
  });
}

export function useCourse(id: number) {
  return useQuery({
    queryKey: [api.courses.get.path, id],
    queryFn: async () => {
      const url = buildUrl(api.courses.get.path, { id });
      const res = await fetch(url, { credentials: "include" });
      if (res.status === 404) return null;
      if (!res.ok) throw new Error("Failed to fetch course");
      const data = await res.json();
      return api.courses.get.responses[200].parse(data);
    },
    enabled: !!id,
  });
}

export function useCreateCourse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: CreateCourseRequest) => {
      const validated = api.courses.create.input.parse(data);
      const res = await fetch(api.courses.create.path, {
        method: api.courses.create.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(validated),
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to create course");
      const json = await res.json();
      return api.courses.create.responses[201].parse(json);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [api.courses.list.path] });
    },
  });
}

export function useUpdateCourse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...updates }: { id: number } & UpdateCourseRequest) => {
      const validated = api.courses.update.input.parse(updates);
      const url = buildUrl(api.courses.update.path, { id });
      const res = await fetch(url, {
        method: api.courses.update.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(validated),
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to update course");
      const json = await res.json();
      return api.courses.update.responses[200].parse(json);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [api.courses.list.path] });
      queryClient.invalidateQueries({ queryKey: [api.courses.get.path, variables.id] });
    },
  });
}

export function useDeleteCourse() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const url = buildUrl(api.courses.delete.path, { id });
      const res = await fetch(url, { method: api.courses.delete.method, credentials: "include" });
      if (!res.ok) throw new Error("Failed to delete course");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [api.courses.list.path] });
    },
  });
}

// ============================================
// DOCUMENTS HOOKS
// ============================================

export function useDocuments(courseId: number) {
  return useQuery({
    queryKey: [api.documents.list.path, courseId],
    queryFn: async () => {
      const url = buildUrl(api.documents.list.path, { courseId });
      const res = await fetch(url, { credentials: "include" });
      if (!res.ok) throw new Error("Failed to fetch documents");
      const data = await res.json();
      return api.documents.list.responses[200].parse(data);
    },
    enabled: !!courseId,
  });
}

export function useCreateDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (data: { courseId: number; title: string; content: string }) => {
      // Manually validating input since we're sending JSON (though API can accept FormData too)
      const payload: CreateDocumentRequest = {
        courseId: data.courseId,
        title: data.title,
        content: data.content,
      };
      
      const res = await fetch(api.documents.create.path, {
        method: api.documents.create.method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        credentials: "include",
      });
      
      if (!res.ok) throw new Error("Failed to create document");
      const json = await res.json();
      return api.documents.create.responses[201].parse(json);
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [api.documents.list.path, variables.courseId] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, courseId }: { id: number; courseId: number }) => {
      const url = buildUrl(api.documents.delete.path, { id });
      const res = await fetch(url, { method: api.documents.delete.method, credentials: "include" });
      if (!res.ok) throw new Error("Failed to delete document");
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: [api.documents.list.path, variables.courseId] });
    },
  });
}
