from tenant_image_gateway.tenant_lifecycle import TenantAccount


def main() -> None:
    account = TenantAccount("acme-demo")
    print(f"created: {account.state}")
    account.activate()
    print(f"ready for image processing: {account.state}")
    account.suspend()
    print(f"admin suspended: {account.state}")


if __name__ == "__main__":
    main()
