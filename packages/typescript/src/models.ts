export interface Entity {
  text:       string;
  entityType: string;
  start:      number;
  end:        number;
  score:      number;
}

export interface Message {
  role:    string;
  content: string | unknown;
  [key:    string]: unknown;
}

export const DEFAULT_ENTITIES = [
  "PERSON",
  "EMAIL",
  "PHONE",
  "ADDRESS",
  "DATE",
  "IP_ADDRESS",
  "FINANCIAL_ID",
  "URL",
];
