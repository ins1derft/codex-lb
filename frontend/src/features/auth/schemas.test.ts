import { describe, expect, it } from "vitest";

import { AuthSessionSchema, LoginRequestSchema } from "@/features/auth/schemas";

describe("AuthSessionSchema", () => {
  it("parses valid auth session payload", () => {
    const parsed = AuthSessionSchema.parse({
      authenticated: true,
      passwordRequired: true,
      totpRequiredOnLogin: false,
      totpConfigured: true,
      user: {
        id: "user_admin",
        username: "admin",
        role: "admin",
      },
      authMode: "trusted_header",
      passwordManagementEnabled: true,
    });

    expect(parsed).toEqual({
      authenticated: true,
      passwordRequired: true,
      totpRequiredOnLogin: false,
      totpConfigured: true,
      user: {
        id: "user_admin",
        username: "admin",
        role: "admin",
      },
      bootstrapRequired: false,
      bootstrapTokenConfigured: false,
      authMode: "trusted_header",
      passwordManagementEnabled: true,
      passwordSessionActive: false,
    });
  });

  it("rejects missing required fields", () => {
    const result = AuthSessionSchema.safeParse({
      authenticated: true,
      passwordRequired: false,
      totpRequiredOnLogin: false,
    });

    expect(result.success).toBe(false);
  });

  it("defaults optional auth mode fields for older responses", () => {
    const parsed = AuthSessionSchema.parse({
      authenticated: true,
      passwordRequired: false,
      totpRequiredOnLogin: false,
      totpConfigured: false,
    });

    expect(parsed.bootstrapRequired).toBe(false);
    expect(parsed.bootstrapTokenConfigured).toBe(false);
    expect(parsed.authMode).toBe("standard");
    expect(parsed.passwordManagementEnabled).toBe(true);
  });
});

describe("LoginRequestSchema", () => {
  it("accepts username and non-empty password", () => {
    expect(
      LoginRequestSchema.safeParse({
        username: "admin",
        password: "strong-password",
      }).success,
    ).toBe(true);
  });

  it("rejects empty username", () => {
    expect(
      LoginRequestSchema.safeParse({
        username: "",
        password: "strong-password",
      }).success,
    ).toBe(false);
  });

  it("rejects empty password", () => {
    expect(
      LoginRequestSchema.safeParse({
        username: "admin",
        password: "",
      }).success,
    ).toBe(false);
  });
});
