using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RegRadar.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class AddAiAnalysisDetailsToRegulatoryEvent : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<string>(
                name: "AiDetailsJson",
                table: "RegulatoryEvents",
                type: "jsonb",
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Domain",
                table: "RegulatoryEvents",
                type: "character varying(128)",
                maxLength: 128,
                nullable: true);

            migrationBuilder.AddColumn<int>(
                name: "ImpactScore",
                table: "RegulatoryEvents",
                type: "integer",
                nullable: true);

            migrationBuilder.AddColumn<bool>(
                name: "ReviewRequired",
                table: "RegulatoryEvents",
                type: "boolean",
                nullable: false,
                defaultValue: false);

            migrationBuilder.AddColumn<string>(
                name: "ReviewState",
                table: "RegulatoryEvents",
                type: "character varying(32)",
                maxLength: 32,
                nullable: true);

            migrationBuilder.AddColumn<string>(
                name: "Urgency",
                table: "RegulatoryEvents",
                type: "character varying(32)",
                maxLength: 32,
                nullable: true);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropColumn(
                name: "AiDetailsJson",
                table: "RegulatoryEvents");

            migrationBuilder.DropColumn(
                name: "Domain",
                table: "RegulatoryEvents");

            migrationBuilder.DropColumn(
                name: "ImpactScore",
                table: "RegulatoryEvents");

            migrationBuilder.DropColumn(
                name: "ReviewRequired",
                table: "RegulatoryEvents");

            migrationBuilder.DropColumn(
                name: "ReviewState",
                table: "RegulatoryEvents");

            migrationBuilder.DropColumn(
                name: "Urgency",
                table: "RegulatoryEvents");
        }
    }
}
