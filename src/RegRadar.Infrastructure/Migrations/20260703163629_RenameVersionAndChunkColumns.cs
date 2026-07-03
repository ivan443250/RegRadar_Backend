using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace RegRadar.Infrastructure.Migrations
{
    /// <inheritdoc />
    public partial class RenameVersionAndChunkColumns : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.RenameColumn(
                name: "VisionNumber",
                table: "DocumentVersions",
                newName: "VersionNumber");

            migrationBuilder.RenameColumn(
                name: "DocumentIndex",
                table: "DocumentChunks",
                newName: "ChunkIndex");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.RenameColumn(
                name: "VersionNumber",
                table: "DocumentVersions",
                newName: "VisionNumber");

            migrationBuilder.RenameColumn(
                name: "ChunkIndex",
                table: "DocumentChunks",
                newName: "DocumentIndex");
        }
    }
}
