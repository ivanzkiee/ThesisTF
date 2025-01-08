<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TenantFlow</title>
    <style>
        body {
            margin: 0;
            font-family: 'Arial', sans-serif;
            background-color: #f9f9f9;
            color: #333;
        }

        .container {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }

        /* Responsive layout for large screens */
        @media (min-width: 768px) {
            .container {
                flex-direction: row;
            }
        }

        .left, .right {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .left {
            background-color: #f1f1f1;
            position: relative;
            text-align: center;
        }

        /* Top-left logo */
        .top-left-logo {
            position: absolute;
            top: 20px;
            left: 20px;
        }

        .top-left-logo img {
            max-width: 500px;
        }

        .left img.main-logo {
            max-width: 300px;
            width: 100%;
            margin-bottom: 20px;
        }

        .left .graphics {
            display: flex;
            gap: 20px;
            justify-content: center;
            margin-bottom: 20px;
        }

        .left .graphics img {
            max-width: 160px;
            height: 59px;
            border-radius: 5px;
        }

        .left h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }

        .left p {
            font-size: 14px;
            color: #666;
        }

        .right {
            padding: 20px;
        }

        .right h2 {
            font-size: 24px;
            margin-bottom: 10px;
        }

        .right p {
            font-size: 14px;
            margin-bottom: 20px;
        }

        .right p a {
            color: #ff5b5b;
            text-decoration: none;
            font-weight: bold;
        }

        form {
            width: 100%;
            max-width: 400px;
        }

        form label {
            display: block;
            font-size: 14px;
            margin-bottom: 5px;
            font-weight: bold;
        }

        form select, form input {
            width: 100%;
            padding: 12px;
            margin-bottom: 20px;
            border: 1px solid #ccc;
            border-radius: 5px;
            font-size: 14px;
        }

        .register-btn {
            width: 100%;
            background-color: #ff5b5b;
            color: white;
            padding: 12px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            font-weight: bold;
        }

        .register-btn:hover {
            background-color: #e04444;
        }

        /* Responsive design for smaller devices */
        @media (max-width: 768px) {
            .left img.main-logo {
                width: 150px;
            }

            .left h1 {
                font-size: 24px;
            }

            .left p {
                font-size: 12px;
            }

            .right h2 {
                font-size: 20px;
            }

            form {
                padding: 10px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Left Section -->
        <div class="left">
            <!-- Top-left logo -->
            <div class="top-left-logo">
                <img src="logo.png" alt="TenantFlow Logo">
            </div>
            
            <!-- Main logo -->
            <img src="Lease with ease.png" alt="Main TenantFlow Logo" class="main-logo">
            
            <!-- Group of two smaller logos -->
            <div class="graphics">
                <img src="logo.png" alt="Logo 1">
            </div>
            <p>Developed for Agustin and Son Realty Development Corporation</p>
        </div>

        <!-- Right Section -->
        <div class="right">
            <h2>Sign up</h2>
            <p>Have an account? <a href="loginui.php">Login here!</a></p>
            <form action="register.php" method="POST">
                <label for="role">I am signing in as:</label>
                <select id="role" name="role" required>
                    <option value="" disabled selected>Choose a role</option>
                    <option value="Admin">Admin</option>
                    <option value="Caretaker">Caretaker/Maintenance</option>
                    <option value="Tenant">Tenant</option>
                </select>

                <label for="email">Email</label>
                <input type="email" id="email" name="email" placeholder="Enter your email address" required>

                <label for="username">Username</label>
                <input type="text" id="username" name="username" placeholder="Enter your Username" required>

                <label for="password">Password</label>
                <input type="password" id="password" name="password" placeholder="Enter your Password" required>

                <label for="confirm_password">Confirm Password</label>
                <input type="password" id="confirm_password" name="confirm_password" placeholder="Confirm your Password" required>

                <button type="submit" class="register-btn">Register</button>
            </form>
        </div>
    </div>
</body>
</html>
