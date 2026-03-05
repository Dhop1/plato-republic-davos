import type { Express, Request, Response } from "express";
import { type Server } from "http";
import http from "http";

const FLASK_PORT = parseInt(process.env.FLASK_PORT || "5001", 10);

function proxyToFlask(req: Request, res: Response) {
  const isMultipart = (req.headers["content-type"] || "").includes("multipart/form-data");
  
  const options: http.RequestOptions = {
    hostname: "127.0.0.1",
    port: FLASK_PORT,
    path: req.originalUrl,
    method: req.method,
    headers: { ...req.headers, host: `127.0.0.1:${FLASK_PORT}` },
  };

  const proxyReq = http.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode || 500, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on("error", (_err) => {
    if (!res.headersSent) {
      res.status(502).json({ message: "Flask backend unavailable" });
    }
  });

  const isFormData = (req.headers["content-type"] || "").includes("application/x-www-form-urlencoded");

  if (req.method === "GET" || req.method === "HEAD" || req.method === "DELETE") {
    proxyReq.end();
  } else if (isMultipart) {
    req.pipe(proxyReq, { end: true });
  } else if (req.rawBody) {
    proxyReq.write(req.rawBody as Buffer);
    proxyReq.end();
  } else if (isFormData && req.body && Object.keys(req.body).length > 0) {
    const params = new URLSearchParams(req.body as Record<string, string>);
    const bodyStr = params.toString();
    proxyReq.setHeader("Content-Type", "application/x-www-form-urlencoded");
    proxyReq.setHeader("Content-Length", Buffer.byteLength(bodyStr));
    proxyReq.write(bodyStr);
    proxyReq.end();
  } else if (req.body && Object.keys(req.body).length > 0) {
    const bodyStr = JSON.stringify(req.body);
    proxyReq.setHeader("Content-Type", "application/json");
    proxyReq.setHeader("Content-Length", Buffer.byteLength(bodyStr));
    proxyReq.write(bodyStr);
    proxyReq.end();
  } else {
    proxyReq.end();
  }
}

export async function registerRoutes(httpServer: Server, app: Express): Promise<Server> {
  // Flask is started by start.sh (gunicorn); Node only proxies to it.
  app.all("/api/*path", proxyToFlask);
  app.get("/static/*path", proxyToFlask);
  app.get("/lesson/:id", proxyToFlask);
  app.all("/signup", proxyToFlask);
  app.all("/login", proxyToFlask);
  app.get("/logout", proxyToFlask);
  app.get("/profile", proxyToFlask);
  app.get("/admin", proxyToFlask);
  app.get("/agora", proxyToFlask);
  app.get("/contact", proxyToFlask);
  app.get("/", proxyToFlask);

  return httpServer;
}
