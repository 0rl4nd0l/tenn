import express from "express";
import { createServer } from "http";
import { existsSync } from "fs";
import path from "path";
import { WebSocketServer } from "ws";

import { OrchestratorService } from "../services/orchestrator";

export async function createHttpServer(service: OrchestratorService) {
  const app = express();
  app.use(express.json({ limit: "1mb" }));

  const webDist = resolveWebDist();
  if (existsSync(webDist)) {
    app.use(express.static(webDist));
  }

  app.get("/api/health", (_request, response) => {
    response.json({ ok: true });
  });

  app.get("/api/board", async (_request, response, next) => {
    try {
      response.json(await service.getBoardState());
    } catch (error) {
      next(error);
    }
  });

  app.get("/api/tasks/:taskId", async (request, response, next) => {
    try {
      const detail = await service.getTaskDetail(request.params.taskId);
      if (!detail) {
        response.status(404).json({ error: "Task not found" });
        return;
      }
      response.json(detail);
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/chat", async (request, response, next) => {
    try {
      response.json(await service.strategistChat(String(request.body?.message ?? "")));
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/tasks/:taskId/retry", async (request, response, next) => {
    try {
      await service.retryTask(request.params.taskId);
      response.json({ ok: true });
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/tasks/:taskId/reassign", async (request, response, next) => {
    try {
      await service.reassignTask(request.params.taskId, request.body?.runtime ?? null);
      response.json({ ok: true });
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/tasks/:taskId/approve", async (request, response, next) => {
    try {
      await service.approveTask(request.params.taskId);
      response.json({ ok: true });
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/tasks/:taskId/reject", async (request, response, next) => {
    try {
      await service.rejectTask(request.params.taskId);
      response.json({ ok: true });
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/tasks/:taskId/reopen", async (request, response, next) => {
    try {
      await service.reopenTask(request.params.taskId);
      response.json({ ok: true });
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/runtimes/refresh", async (_request, response, next) => {
    try {
      await service.refreshCapabilitySnapshots();
      response.json({ ok: true });
    } catch (error) {
      next(error);
    }
  });

  app.post("/api/tick", async (_request, response, next) => {
    try {
      await service.scheduleNow({ force: true });
      response.json({ ok: true });
    } catch (error) {
      next(error);
    }
  });

  app.get("*", (request, response, next) => {
    const indexFile = path.join(webDist, "index.html");
    if (request.path.startsWith("/api") || !existsSync(indexFile)) {
      next();
      return;
    }
    response.sendFile(indexFile);
  });

  app.use((error: Error, _request: express.Request, response: express.Response, _next: express.NextFunction) => {
    response.status(500).json({ error: error.message });
  });

  const httpServer = createServer(app);
  const wss = new WebSocketServer({ server: httpServer, path: "/ws" });

  service.on("refresh", (payload) => {
    const message = JSON.stringify({ type: "refresh", payload });
    for (const client of wss.clients) {
      if (client.readyState === client.OPEN) {
        client.send(message);
      }
    }
  });

  return { app, httpServer, wss };
}

function resolveWebDist(): string {
  const candidates = [
    path.resolve(process.cwd(), "dist/web"),
    path.resolve(__dirname, "../../../dist/web"),
    path.resolve(__dirname, "../../../../web")
  ];
  return candidates.find((candidate) => existsSync(candidate)) ?? path.resolve(process.cwd(), "dist/web");
}
