import type { Express, Request, Response } from "express";
import { type Server } from "http";
import http from "http";
import { spawn } from "child_process";

const FLASK_PORT = 5001;

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

  if (req.method === "GET" || req.method === "HEAD" || req.method === "DELETE") {
    proxyReq.end();
  } else if (isMultipart) {
    req.pipe(proxyReq, { end: true });
  } else if (req.rawBody) {
    proxyReq.write(req.rawBody as Buffer);
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
  const flaskProc = spawn("python", ["main.py"], {
    cwd: process.cwd(),
    env: { ...process.env, FLASK_PORT: String(FLASK_PORT) },
    stdio: ["ignore", "inherit", "inherit"],
  });

  flaskProc.on("error", (err) => {
    console.error("Failed to start Flask:", err);
  });

  flaskProc.on("exit", (code) => {
    if (code !== null && code !== 0) {
      console.error(`Flask process exited with code ${code}`);
    }
  });

  await new Promise((resolve) => setTimeout(resolve, 3000));

  app.all("/api/*path", proxyToFlask);
  app.get("/static/*path", proxyToFlask);
  app.get("/lesson/:id", proxyToFlask);
  app.get("/", proxyToFlask);

  return httpServer;
}
