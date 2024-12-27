<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TenantFlow</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-color: #f0f0f0;
        }

        .container {
            display: flex;
            width: 90%;
            max-width: 1200px;
            background-color: #fff;
            border-radius: 10px;
            box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }

        .left {
            flex: 1;
            background-color: #f7f7f7;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            padding: 40px;
        }

        .left img {
            max-width: 80%;
            height: auto;
            margin-bottom: 20px;
        }

        .left p {
            font-size: 24px;
            font-weight: bold;
            color: #333;
        }

        .right {
            flex: 1;
            padding: 40px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .right h2 {
            font-size: 28px;
            color: #333;
            margin-bottom: 10px;
        }

        .right p {
            font-size: 14px;
            margin-bottom: 20px;
        }

        .right a {
            color: #e53935;
            text-decoration: none;
            font-weight: bold;
        }

        .right a:hover {
            text-decoration: underline;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            font-size: 14px;
            color: #555;
            margin-bottom: 5px;
        }

        .form-group input {
            width: 100%;
            padding: 10px;
            font-size: 14px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }

        .form-group input:focus {
            border-color: #e53935;
            outline: none;
        }

        .form-options {
            display: flex;
            justify-content: space-between;
            font-size: 14px;
            margin-bottom: 20px;
        }

        .form-options a {
            color: #e53935;
        }

        .form-options a:hover {
            text-decoration: underline;
        }

        .login-button {
            width: 100%;
            background-color: #e53935;
            color: #fff;
            padding: 12px;
            font-size: 16px;
            font-weight: bold;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }

        .login-button:hover {
            background-color: #d32f2f;
        }

        .footer {
            margin-top: 20px;
            font-size: 10px;
            color: #888;
            text-align: center;
        }

        .logo-top-left{
            position: absolute;
            width: 150px;
            height: auto
        }

        .logo-top-left {
            top: 30px;
            left: 130px;
        }
    </style>
</head>
<body>
    <!-- Top-Left Logo -->
    <img src="logo.png" alt="TenantFlow Logo" class="logo-top-left">

    <div class="container">
        <!-- Left Section -->
        <div class="left">
            <img src="Lease with ease.png" alt="Lease With Ease">
        </div>

        <!-- Right Section -->
         
        <div class="right">
            <h2>Sign in</h2>
            <p>New here? <a href="signup.php">Sign up here!</a></p>
            <form action="#" method="post">
                <div class="form-group">
                    <label for="email">Email</label>
                    <input type="email" id="email" name="email" placeholder="Enter your email address" required>
                </div>
                <div class="form-group">
                    <label for="password">Password</label>
                    <input type="password" id="password" name="password" placeholder="Enter your password" required>
                </div>
                <div class="form-options">
                    <label>
                        <input type="checkbox" name="remember"> Remember me
                    </label>
                    <a href="#">Forgot Password?</a>
                </div>
                <button type="submit" class="login-button">Login</button>
            </form>  
             <div class="left">
            <img src="logo.png" alt="Logo">
        </div>
            <div class="footer">
                Developed for Agustin and Son Realty Development Corporation
            </div>
        </div>
    </div>
</body>
</html>
