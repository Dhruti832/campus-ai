import type { Conversation } from "@/components/chat/types";

import {
  loadActiveConversationId,
  loadConversations,
  saveActiveConversationId,
  saveConversations,
} from "../conversationStorage";

describe("conversationStorage", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  describe("loadConversations", () => {
    it("returns an empty array when nothing is stored", () => {
      expect(loadConversations()).toEqual([]);
    });

    it("returns previously saved conversations", () => {
      const conversations: Conversation[] = [
        { id: "1", title: "hi", messages: [], updatedAt: 100 },
      ];
      saveConversations(conversations);
      expect(loadConversations()).toEqual(conversations);
    });

    it("returns an empty array for malformed stored data", () => {
      window.localStorage.setItem("campus-ai-conversations", "not json");
      expect(loadConversations()).toEqual([]);
    });

    it("returns an empty array when the stored value isn't an array", () => {
      window.localStorage.setItem("campus-ai-conversations", JSON.stringify({ not: "an array" }));
      expect(loadConversations()).toEqual([]);
    });
  });

  describe("saveConversations", () => {
    it("persists conversations that loadConversations can read back", () => {
      const conversations: Conversation[] = [
        {
          id: "1",
          title: "hi",
          messages: [{ id: "m1", role: "user", text: "hi" }],
          updatedAt: 200,
        },
      ];
      saveConversations(conversations);
      expect(loadConversations()).toEqual(conversations);
    });
  });

  describe("active conversation id", () => {
    it("returns null when nothing is stored", () => {
      expect(loadActiveConversationId()).toBeNull();
    });

    it("persists and reads back the active conversation id", () => {
      saveActiveConversationId("abc123");
      expect(loadActiveConversationId()).toBe("abc123");
    });
  });
});
