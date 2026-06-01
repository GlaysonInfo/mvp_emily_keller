output "alb_dns_name" {
  description = "DNS do ALB (aponte o registro do app para ele)"
  value       = aws_lb.app.dns_name
}

output "alb_zone_id" {
  description = "Zone ID do ALB (para registro ALIAS no Route 53)"
  value       = aws_lb.app.zone_id
}

output "alb_security_group_id" {
  value       = aws_security_group.alb.id
  description = "SG do ALB"
}

output "instance_security_group_id" {
  description = "Anexe este SG na instancia EC2 (ela passa a aceitar apenas o ALB)"
  value       = aws_security_group.instance.id
}
