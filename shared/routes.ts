import { z } from 'zod';
import { insertCourseSchema, insertDocumentSchema, courses, documents } from './schema';

// ============================================
// SHARED ERROR SCHEMAS
// ============================================
export const errorSchemas = {
  validation: z.object({
    message: z.string(),
    field: z.string().optional(),
  }),
  notFound: z.object({
    message: z.string(),
  }),
  internal: z.object({
    message: z.string(),
  }),
};

// ============================================
// API CONTRACT
// ============================================
export const api = {
  courses: {
    list: {
      method: 'GET' as const,
      path: '/api/courses' as const,
      responses: {
        200: z.array(z.custom<typeof courses.$inferSelect>()),
      },
    },
    get: {
      method: 'GET' as const,
      path: '/api/courses/:id' as const,
      responses: {
        200: z.custom<typeof courses.$inferSelect>(),
        404: errorSchemas.notFound,
      },
    },
    create: {
      method: 'POST' as const,
      path: '/api/courses' as const,
      input: insertCourseSchema,
      responses: {
        201: z.custom<typeof courses.$inferSelect>(),
        400: errorSchemas.validation,
      },
    },
    update: {
      method: 'PUT' as const,
      path: '/api/courses/:id' as const,
      input: insertCourseSchema.partial(),
      responses: {
        200: z.custom<typeof courses.$inferSelect>(),
        400: errorSchemas.validation,
        404: errorSchemas.notFound,
      },
    },
    delete: {
      method: 'DELETE' as const,
      path: '/api/courses/:id' as const,
      responses: {
        204: z.void(),
        404: errorSchemas.notFound,
      },
    },
  },
  documents: {
    list: {
      method: 'GET' as const,
      path: '/api/courses/:courseId/documents' as const,
      responses: {
        200: z.array(z.custom<typeof documents.$inferSelect>()),
      },
    },
    create: {
      method: 'POST' as const,
      path: '/api/documents' as const,
      // Input is FormData, so we don't strictly validate body here in the same way, 
      // but we can define the expected fields if we were sending JSON.
      // For file uploads, we usually handle FormData manually or define a schema for the metadata.
      input: insertDocumentSchema, 
      responses: {
        201: z.custom<typeof documents.$inferSelect>(),
        400: errorSchemas.validation,
      },
    },
    delete: {
      method: 'DELETE' as const,
      path: '/api/documents/:id' as const,
      responses: {
        204: z.void(),
        404: errorSchemas.notFound,
      },
    },
  },
};

export function buildUrl(path: string, params?: Record<string, string | number>): string {
  let url = path;
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (url.includes(`:${key}`)) {
        url = url.replace(`:${key}`, String(value));
      }
    });
  }
  return url;
}
