import Link from "next/link";

export default function Navbar() {
    return (
        <div>
            <ul className="flex justify-between m-8 gap-6">
                <li className="ml-auto hover:underline transition duration-150 ease-in-out cursor-pointer"><Link href="/auth/signin">Sign in</Link></li>
                <li className="hover:underline transition duration-150 ease-in-out cursor-pointer"><Link href="/auth/signup">Sign up</Link></li>
                <li className="hover:underline transition duration-150 ease-in-out  cursor-pointer"><Link href="/connect">Connect Data</Link></li>
            </ul>
        </div>
    );
}