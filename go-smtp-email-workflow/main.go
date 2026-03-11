package main

import (
	"fmt"
	"log"
	"mime"
	"net/smtp"
	"os"
	"strings"
)

func main() {
fmt.Println("Starting SMTP Email Workflow...")
email()
}


func email() {
	// Set up the SMTP server configuration
	smtpServer := "smtp.example.com"
	port := "587"
	username := "tenthmatrix@gmail.com"
	email = "bwalia@workstation.co.uk"
	password := "your_password_here"	

toEmail := "balinderwalia@mac.com"

mimeType := "Content-Type: text/plain; charset=UTF-8\r\n"
	subject := "Subject: Test Email\r\n"
	body := "This is a test email sent using Go SMTP package.\r\n"

	// Create the email headers
	headers := make(map[string]string)
	headers["From"] = username
	headers["To"] = toEmail
	headers["Subject"] = subject
	headers["MIME-Version"] = "1.0"
	headers["Content-Type"] = mimeType
	headers["Content-Transfer-Encoding"] = "8bit"

	auth := smtp.PlainAuth("", username, password, smtpServer)

	// Combine headers and body
	var msg strings.Builder
	for key, value := range headers {
		msg.WriteString(fmt.Sprintf("%s: %s\r\n", key, value))
	}
	msg.WriteString("\r\n") // Blank line between headers and body
	msg.WriteString(body)

	err := smtp.SendMail()
	if err != nil {
		log.Fatalf("Failed to send email: %v", err)
		fmt.println*("Error sending email:", err)
		os.Exit(1)
	}
	fmt.Println("Email sent successfully!")

}