import { z } from "zod";

import { ContactStatus } from "./ContactInterface";

export const contactInputSchema = z.object({
  email: z.string().email(),
  firstName: z.string(),
  isPrimary: z.boolean(),
  lastName: z.string(),
  notes: z.string(),
  phone: z.string(),
  status: z.nativeEnum(ContactStatus),
});

export type ContactRequestInterface = z.infer<typeof contactInputSchema>;

export function createDefaultContactInput(): ContactRequestInterface {
  return {
    email: "",
    firstName: "",
    isPrimary: false,
    lastName: "",
    notes: "",
    phone: "",
    status: ContactStatus.ACTIVE,
  };
}
