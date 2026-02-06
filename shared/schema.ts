import { pgTable, text, serial, integer, boolean, timestamp, jsonb } from "drizzle-orm/pg-core";
import { relations } from "drizzle-orm";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

// Import Auth and Chat schemas from blueprints
export * from "./models/auth";
export * from "./models/chat";

import { users } from "./models/auth";

// === TABLE DEFINITIONS ===

export const courses = pgTable("courses", {
  id: serial("id").primaryKey(),
  title: text("title").notNull(),
  description: text("description").notNull(),
  instructorId: text("instructor_id").references(() => users.id),
  coverImageUrl: text("cover_image_url"),
  createdAt: timestamp("created_at").defaultNow(),
});

export const documents = pgTable("documents", {
  id: serial("id").primaryKey(),
  courseId: integer("course_id").notNull().references(() => courses.id, { onDelete: 'cascade' }),
  title: text("title").notNull(),
  content: text("content").notNull(), // Extracted text content
  createdAt: timestamp("created_at").defaultNow(),
});

// === RELATIONS ===
export const coursesRelations = relations(courses, ({ one, many }) => ({
  instructor: one(users, {
    fields: [courses.instructorId],
    references: [users.id],
  }),
  documents: many(documents),
}));

export const documentsRelations = relations(documents, ({ one }) => ({
  course: one(courses, {
    fields: [documents.courseId],
    references: [courses.id],
  }),
}));

// === BASE SCHEMAS ===
export const insertCourseSchema = createInsertSchema(courses).omit({ id: true, createdAt: true });
export const insertDocumentSchema = createInsertSchema(documents).omit({ id: true, createdAt: true });

// === TYPES ===
export type Course = typeof courses.$inferSelect;
export type InsertCourse = z.infer<typeof insertCourseSchema>;
export type Document = typeof documents.$inferSelect;
export type InsertDocument = z.infer<typeof insertDocumentSchema>;

// Request types
export type CreateCourseRequest = InsertCourse;
export type UpdateCourseRequest = Partial<InsertCourse>;
export type CreateDocumentRequest = InsertDocument;
