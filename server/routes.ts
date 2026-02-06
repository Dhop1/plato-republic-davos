import type { Express, Request, Response } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";
import { setupAuth, registerAuthRoutes } from "./replit_integrations/auth";
import { chatStorage } from "./replit_integrations/chat";
import { ai } from "./replit_integrations/image"; // Re-using AI client
import multer from "multer";
import { api } from "@shared/routes";
import { z } from "zod";
import { insertCourseSchema, insertDocumentSchema } from "@shared/schema";
import { Modality } from "@google/genai";

const upload = multer({ storage: multer.memoryStorage() });

export async function registerRoutes(httpServer: Server, app: Express): Promise<Server> {
  // Setup Auth
  await setupAuth(app);
  registerAuthRoutes(app);

  // === COURSES ===
  app.get(api.courses.list.path, async (req, res) => {
    const courses = await storage.getCourses();
    res.json(courses);
  });

  app.get(api.courses.get.path, async (req, res) => {
    const course = await storage.getCourse(Number(req.params.id));
    if (!course) return res.status(404).json({ message: "Course not found" });
    res.json(course);
  });

  app.post(api.courses.create.path, async (req, res) => {
    try {
      const input = api.courses.create.input.parse(req.body);
      const course = await storage.createCourse(input);
      res.status(201).json(course);
    } catch (err) {
      if (err instanceof z.ZodError) {
        return res.status(400).json({ message: err.errors[0].message });
      }
      res.status(500).json({ message: "Internal Server Error" });
    }
  });

  // === DOCUMENTS ===
  app.get(api.documents.list.path, async (req, res) => {
    const docs = await storage.getDocuments(Number(req.params.courseId));
    res.json(docs);
  });

  app.post(api.documents.create.path, upload.single('file'), async (req, res) => {
    try {
      // Validate metadata
      const body = {
        title: req.body.title,
        courseId: Number(req.body.courseId),
        content: "", // Placeholder, will fill from file
      };
      
      if (!req.file) {
        return res.status(400).json({ message: "No file uploaded" });
      }

      // Read text content from file
      const textContent = req.file.buffer.toString('utf-8');
      body.content = textContent;

      const input = insertDocumentSchema.parse(body);
      const doc = await storage.createDocument(input);
      res.status(201).json(doc);
    } catch (err) {
      console.error(err);
      if (err instanceof z.ZodError) {
        return res.status(400).json({ message: err.errors[0].message });
      }
      res.status(500).json({ message: "Internal Server Error" });
    }
  });

  // === CHAT (Custom Implementation) ===
  
  // Get conversations (optionally filtered by courseId)
  app.get("/api/conversations", async (req, res) => {
    const courseId = req.query.courseId ? Number(req.query.courseId) : undefined;
    const conversations = await chatStorage.getAllConversations(courseId);
    res.json(conversations);
  });

  // Get single conversation
  app.get("/api/conversations/:id", async (req, res) => {
    const id = Number(req.params.id);
    const conversation = await chatStorage.getConversation(id);
    if (!conversation) return res.status(404).json({ message: "Conversation not found" });
    const messages = await chatStorage.getMessagesByConversation(id);
    res.json({ ...conversation, messages });
  });

  // Create conversation
  app.post("/api/conversations", async (req, res) => {
    const { title, courseId } = req.body;
    const conversation = await chatStorage.createConversation(title || "New Chat", courseId);
    res.status(201).json(conversation);
  });

  // Send Message & Stream Response
  app.post("/api/conversations/:id/messages", async (req, res) => {
    try {
      const conversationId = Number(req.params.id);
      const { content } = req.body;

      // 1. Get conversation to check courseId
      const conversation = await chatStorage.getConversation(conversationId);
      if (!conversation) return res.status(404).json({ message: "Conversation not found" });

      // 2. Save user message
      await chatStorage.createMessage(conversationId, "user", content);

      // 3. Gather Context (Documents)
      let context = "";
      if (conversation.courseId) {
        const docs = await storage.getDocuments(conversation.courseId);
        if (docs.length > 0) {
          context = "Context from uploaded documents:\n" + docs.map(d => `--- Document: ${d.title} ---\n${d.content}\n`).join("\n") + "\n\n";
        }
      }

      // 4. Build Chat History
      const messages = await chatStorage.getMessagesByConversation(conversationId);
      
      // Filter out the one we just added to avoid duplication if we re-fetch? 
      // Actually `getMessagesByConversation` includes the one we just added.
      // We should format them for Gemini.
      
      const history = messages.slice(0, -1).map(m => ({
        role: m.role === 'user' ? 'user' : 'model',
        parts: [{ text: m.content }]
      }));

      // System prompt / Context injection
      // Gemini 2.5 supports system instructions, or we can just prepend to the first message or the current message.
      // We'll prepend context to the LAST user message (the current one) effectively.
      // Or better: Prepend to the prompt.
      
      const fullPrompt = `${context}User Question: ${content}`;

      // 5. Stream from Gemini
      res.setHeader("Content-Type", "text/event-stream");
      res.setHeader("Cache-Control", "no-cache");
      res.setHeader("Connection", "keep-alive");

      const stream = await ai.models.generateContentStream({
        model: "gemini-2.5-flash",
        contents: [
          ...history as any,
          { role: "user", parts: [{ text: fullPrompt }] }
        ],
      });

      let fullResponse = "";

      for await (const chunk of stream) {
        const text = chunk.text();
        if (text) {
          fullResponse += text;
          res.write(`data: ${JSON.stringify({ content: text })}\n\n`);
        }
      }

      // 6. Save assistant message
      await chatStorage.createMessage(conversationId, "model", fullResponse);

      res.write(`data: ${JSON.stringify({ done: true })}\n\n`);
      res.end();

    } catch (error) {
      console.error("Chat error:", error);
      if (!res.headersSent) {
        res.status(500).json({ message: "Failed to generate response" });
      } else {
        res.write(`data: ${JSON.stringify({ error: "Stream failed" })}\n\n`);
        res.end();
      }
    }
  });

  // Seed Database
  const existingCourses = await storage.getCourses();
  if (existingCourses.length === 0) {
    await storage.createCourse({
      title: "The Republic: Book I - The Definition of Justice",
      description: "Socrates discusses the meaning of justice with Cephalus, Polemarchus, and Thrasymachus. Is it speaking the truth and paying debts? Or is it the advantage of the stronger?",
      instructorId: null,
      coverImageUrl: "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?q=80&w=2070&auto=format&fit=crop"
    });
    await storage.createCourse({
      title: "The Republic: Book VII - The Allegory of the Cave",
      description: "Plato's famous allegory concerning the nature of education and the lack of it in our nature. The journey from shadows to the light of the sun.",
      instructorId: null,
      coverImageUrl: "https://images.unsplash.com/photo-1535905557558-afc4877a26fc?q=80&w=1974&auto=format&fit=crop"
    });
  }

  return httpServer;
}
