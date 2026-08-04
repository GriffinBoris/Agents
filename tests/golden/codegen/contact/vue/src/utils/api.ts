import type { ContactInterface } from "@/types/contact/ContactInterface";
import type { ContactRequestInterface } from "@/types/contact/ContactRequestInterface";

const contacts = {
  list: (organizationId: number) =>
    apiClient.get<ContactInterface[]>(
      `api/organizations/${organizationId}/contacts/list/`
    ),
  create: (organizationId: number, payload: ContactRequestInterface) =>
    apiClient.post<ContactInterface, ContactRequestInterface>(
      `api/organizations/${organizationId}/contacts/create/`,
      payload
    ),
  detail: (organizationId: number, contactId: number) =>
    apiClient.get<ContactInterface>(
      `api/organizations/${organizationId}/contacts/${contactId}/`
    ),
  update: (organizationId: number, contactId: number, payload: Partial<ContactRequestInterface>) =>
    apiClient.put<ContactInterface, Partial<ContactRequestInterface>>(
      `api/organizations/${organizationId}/contacts/${contactId}/`,
      payload
    ),
};
