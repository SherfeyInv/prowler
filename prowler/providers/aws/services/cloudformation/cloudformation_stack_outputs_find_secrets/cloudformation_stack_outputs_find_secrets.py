import os
import tempfile

from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings

from prowler.lib.check.models import Check, Check_Report_AWS
from prowler.providers.aws.services.cloudformation.cloudformation_client import (
    cloudformation_client,
)


class cloudformation_stack_outputs_find_secrets(Check):
    """Check if a CloudFormation Stack has secrets in their Outputs"""

    def execute(self):
        """Execute the cloudformation_stack_outputs_find_secrets check"""
        findings = []
        for stack in cloudformation_client.stacks:
            report = Check_Report_AWS(self.metadata())
            report.region = stack.region
            report.resource_id = stack.name
            report.resource_arn = stack.arn
            report.resource_tags = stack.tags
            report.status = "PASS"
            report.status_extended = f"No secrets found in Stack {stack.name} Outputs."
            if stack.outputs:
                temp_output_file = tempfile.NamedTemporaryFile(delete=False)

                # Store the CloudFormation Stack Outputs into a file
                for output in stack.outputs:
                    temp_output_file.write(
                        bytes(
                            f"{output}\n",
                            encoding="raw_unicode_escape",
                        )
                    )
                temp_output_file.close()

                # Init detect_secrets
                secrets = SecretsCollection()
                # Scan file for secrets
                with default_settings():
                    secrets.scan_file(temp_output_file.name)

                detect_secrets_output = secrets.json()
                # If secrets are found, update the report status
                if detect_secrets_output:
                    secrets_string = ", ".join(
                        [
                            f"{secret['type']} in Output {int(secret['line_number'])}"
                            for secret in detect_secrets_output[temp_output_file.name]
                        ]
                    )
                    report.status = "FAIL"
                    report.status_extended = f"Potential secret found in Stack {stack.name} Outputs -> {secrets_string}."

                os.remove(temp_output_file.name)
            else:
                report.status = "PASS"
                report.status_extended = f"CloudFormation {stack.name} has no Outputs."

            findings.append(report)

        return findings
