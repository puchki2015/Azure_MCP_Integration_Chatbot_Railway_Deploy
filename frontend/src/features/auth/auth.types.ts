export type AppUser = {
  oid: string;
  email: string;
  displayName: string;
  isAdmin: boolean;
};

export type AuthState = {
  status: "loading" | "unauthenticated" | "authenticated";
  user: AppUser | null;
  accessToken: string | null;
};
