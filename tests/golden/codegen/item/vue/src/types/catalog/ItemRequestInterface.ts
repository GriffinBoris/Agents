import { z } from "zod";

export const itemInputSchema = z.object({
  code: z.string(),
  name: z.string().min(1, "Name is required"),
  sortOrder: z.number(),
  summary: z.string(),
});

export type ItemRequestInterface = z.infer<typeof itemInputSchema>;

export function createDefaultItemInput(): ItemRequestInterface {
  return {
    code: "",
    name: "",
    sortOrder: 0,
    summary: "",
  };
}
