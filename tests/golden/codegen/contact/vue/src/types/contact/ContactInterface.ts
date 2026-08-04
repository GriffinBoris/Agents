export enum ContactStatus {
  ACTIVE = "ACTIVE",
  INACTIVE = "INACTIVE",
}

export interface ContactInterface {
  email: string;
  firstName: string;
  isPrimary: boolean;
  lastName: string;
  notes: string;
  organization: number;
  phone: string;
  status: ContactStatus;
  createdTs: string;
  updatedTs: string;
  id: number;
}
