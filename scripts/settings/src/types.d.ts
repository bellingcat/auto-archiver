export interface Config {
  name: string;
  description: string;
  type: string?;
  default: any;
  help: string;
  choices: string[];
  required: boolean;
}

interface Manifest {
  description: string;
}

export interface Module {
  name: string;
  description: string;
  configs: { [key: string]: Config };
  manifest: Manifest;
  display_name: string;
}
