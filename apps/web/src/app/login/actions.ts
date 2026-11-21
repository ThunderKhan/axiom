"use server";

import { revalidatePath } from "next/cache";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { publicAuthConfig } from "../../lib/auth-config";
import { safeReturnPath } from "../../lib/redirects";
import { createServerAuthClient } from "../../lib/supabase/server";

export type LoginState = Readonly<{ message: string }>;
const invalidLogin =
  "We could not sign you in. Check your details and try again.";
const unavailable =
  "Sign-in is temporarily unavailable. Please try again later.";

export async function signIn(
  _previous: LoginState,
  form: FormData,
): Promise<LoginState> {
  const email = form.get("email");
  const password = form.get("password");
  const destination = safeReturnPath(form.get("returnTo"));
  if (
    typeof email !== "string" ||
    email.length < 3 ||
    email.length > 254 ||
    !email.includes("@") ||
    typeof password !== "string" ||
    password.length < 1 ||
    password.length > 4096
  ) {
    return { message: invalidLogin };
  }
  if (!publicAuthConfig()) {
    return { message: "Sign-in is not configured for this environment." };
  }
  try {
    const supabase = await createServerAuthClient(true);
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (error || !data.session) {
      return {
        message:
          error?.status && error.status >= 500 ? unavailable : invalidLogin,
      };
    }
    // A successful password response is not the final trust decision.
    const result = await supabase.auth.getClaims();
    const claims = result.data?.claims;
    if (
      result.error ||
      !claims ||
      typeof claims.sub !== "string" ||
      claims.role !== "authenticated" ||
      claims.is_anonymous === true
    ) {
      await supabase.auth.signOut({ scope: "local" });
      return { message: unavailable };
    }
  } catch {
    // Never report the provider's raw response or any sensitive credentials.
    return { message: unavailable };
  }
  revalidatePath("/app", "page");
  redirect(destination);
}

export async function signOut(): Promise<never> {
  let remoteUnconfirmed = false;
  if (publicAuthConfig()) {
    try {
      const supabase = await createServerAuthClient(true);
      const result = await supabase.auth.signOut();
      if (result.error) {
        remoteUnconfirmed = true;
        // A successful global sign-out already clears the local session.
        // Retry local-only cleanup only when global revocation was unconfirmed.
        await supabase.auth.signOut({ scope: "local" });
      }
    } catch {
      remoteUnconfirmed = true;
    }
  } else {
    remoteUnconfirmed = true;
  }
  // Defense in depth: eliminate Supabase SSR cookies if remote sign-out is down.
  const store = await cookies();
  for (const cookie of store.getAll()) {
    if (/^sb-[A-Za-z0-9_-]+-auth-token(?:\.[0-9]+)?$/.test(cookie.name)) {
      store.delete(cookie.name);
    }
  }
  revalidatePath("/app", "page");
  redirect(
    "/login?notice=" + (remoteUnconfirmed ? "signed-out-local" : "signed-out"),
  );
}
