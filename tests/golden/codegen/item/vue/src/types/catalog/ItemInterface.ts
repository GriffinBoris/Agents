export enum ItemStatus {
  ACTIVE = "ACTIVE",
  INACTIVE = "INACTIVE",
}

export interface ItemInterface {
  catalogEntry: number;
  code: string;
  name: string;
  sortOrder: number;
  status: ItemStatus;
  summary: string;
  createdTs: string;
  updatedTs: string;
  id: number;
}
