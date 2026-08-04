import type { ItemInterface } from "@/types/catalog/ItemInterface";
import type { ItemRequestInterface } from "@/types/catalog/ItemRequestInterface";

const items = {
  list: (organizationId: number, workspaceId: number, catalogEntryId: number) =>
    apiClient.get<ItemInterface[]>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/catalog-entries/${catalogEntryId}/items/list/`
    ),
  create: (organizationId: number, workspaceId: number, catalogEntryId: number, payload: ItemRequestInterface) =>
    apiClient.post<ItemInterface, ItemRequestInterface>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/catalog-entries/${catalogEntryId}/items/create/`,
      payload
    ),
  detail: (organizationId: number, workspaceId: number, catalogEntryId: number, itemId: number) =>
    apiClient.get<ItemInterface>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/catalog-entries/${catalogEntryId}/items/${itemId}/`
    ),
  update: (organizationId: number, workspaceId: number, catalogEntryId: number, itemId: number, payload: Partial<ItemRequestInterface>) =>
    apiClient.put<ItemInterface, Partial<ItemRequestInterface>>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/catalog-entries/${catalogEntryId}/items/${itemId}/`,
      payload
    ),
  archive: (organizationId: number, workspaceId: number, catalogEntryId: number, itemId: number) =>
    apiClient.post<ItemInterface, undefined>(
      `api/organizations/${organizationId}/workspaces/${workspaceId}/catalog-entries/${catalogEntryId}/items/${itemId}/archive/`,
      undefined
    ),
};
