import { NextResponse } from 'next/server';

export async function POST(request: Request) {
    try {
        const body = await request.json();
        
        const { username, password } = body;

        // Check credentials
        if (username === 'admin@minimart.com' && password === 'password123') {
            const token = 'mock-jwt-token-for-demo';
            
            const response = NextResponse.json({ 
                success: true,
                user: { name: 'Admin User', username: 'admin@minimart.com' }
            });

            response.cookies.set('auth_token', token, {
                httpOnly: true,
                secure: process.env.NODE_ENV === 'production',
                sameSite: 'lax',
                maxAge: 60 * 60 * 24 // 1 day
            });

            return response;
        }

        return NextResponse.json(
            { error: 'Invalid credentials' },
            { status: 401 }
        );

    } catch (error) {
        console.error('Login error:', error);
        return NextResponse.json(
            { error: 'Internal server error' },
            { status: 500 }
        );
    }
}