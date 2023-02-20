    provisioner "remote-exec" {
        inline = [
             "chmod +x /tmp/kickstart_ec2.sh",
             "sudo /bin/bash /tmp/kickstart_ec2.sh"
        ]
    }    
