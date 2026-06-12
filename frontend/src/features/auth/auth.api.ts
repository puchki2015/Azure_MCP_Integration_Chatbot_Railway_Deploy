import { request } from "../../services/api";
import type { AppUser } from "./auth.types";

type CurrentUserResponse = {
  oid: string;
  email: string;
  display_name: string;
  is_admin?: boolean;
};

export function fetchCurrentUser() {
  return request<CurrentUserResponse>("/me").then((user) => ({
    oid: user.oid,
    email: user.email,
    displayName: user.display_name,
    isAdmin: user.is_admin ?? false
  }));
}
