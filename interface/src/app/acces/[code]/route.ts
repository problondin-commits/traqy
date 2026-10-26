// Lien d'accès personnel : /acces/<code>. Un code valide est gardé dans un cookie protégé,
// puis la personne arrive sur ses dossiers. Un code inconnu mène à la démo, sans rien révéler.
import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { COOKIE_ACCES, roleDuCode } from "@/lib/acces";
import { COOKIE_IMPORT } from "@/lib/donnees";

const UN_AN = 60 * 60 * 24 * 365;

export async function GET(requete: Request, { params }: RouteContext<"/acces/[code]">) {
  const { code } = await params;
  const role = roleDuCode(code);
  const pot = await cookies();
  pot.delete(COOKIE_IMPORT);
  if (role) {
    pot.set(COOKIE_ACCES, code, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", maxAge: UN_AN, path: "/" });
  } else {
    pot.delete(COOKIE_ACCES);
  }
  return NextResponse.redirect(new URL(role ? "/catalogue" : "/depot", requete.url));
}
