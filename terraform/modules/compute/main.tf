data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

# ──── IAM ────
resource "aws_iam_role" "gateway" {
  name = "${var.project}-gateway-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "cloudwatch" {
  role       = aws_iam_role.gateway.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
}

resource "aws_iam_role_policy_attachment" "ssm" {
  role       = aws_iam_role.gateway.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "gateway" {
  name = "${var.project}-gateway-profile"
  role = aws_iam_role.gateway.name
}

# ──── ALB ────
resource "aws_lb" "gateway" {
  name               = "${var.project}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [var.alb_security_group_id]
  subnets            = var.public_subnet_ids
  tags               = { Name = "${var.project}-alb" }
}

resource "aws_lb_target_group" "gateway" {
  name     = "${var.project}-tg"
  port     = 8080
  protocol = "HTTP"
  vpc_id   = var.vpc_id

  health_check {
    path                = "/healthz"
    port                = "8080"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 15
    matcher             = "200"
  }
  deregistration_delay = 30
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.gateway.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.gateway.arn
  }
}

# ──── Launch Template ────
resource "aws_launch_template" "gateway" {
  name_prefix   = "${var.project}-lt-"
  image_id      = data.aws_ami.amazon_linux.id
  instance_type = "t3.micro"
  key_name      = var.key_pair_name

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 20
      volume_type           = "gp2"
      delete_on_termination = true
    }
  }

  vpc_security_group_ids = [var.gateway_security_group_id]

  iam_instance_profile {
    name = aws_iam_instance_profile.gateway.name
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh", {
    redis_host    = var.redis_host
    redis_port    = var.redis_port
    django_secret = var.django_secret_key
    allowed_hosts = var.allowed_hosts
  }))

  tag_specifications {
    resource_type = "instance"
    tags = { Name = "${var.project}-gateway" }
  }

  lifecycle { create_before_destroy = true }
}

# ──── ASG ────
resource "aws_autoscaling_group" "gateway" {
  name                = "${var.project}-asg"
  desired_capacity    = 1
  min_size            = 1
  max_size            = 2
  vpc_zone_identifier = var.public_subnet_ids
  target_group_arns   = [aws_lb_target_group.gateway.arn]

  launch_template {
    id      = aws_launch_template.gateway.id
    version = "$Latest"
  }

  health_check_type         = "ELB"
  health_check_grace_period = 420
  default_cooldown          = 120

  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 0
    }
  }

  tag {
    key                 = "Name"
    value               = "${var.project}-gateway"
    propagate_at_launch = true
  }
}
