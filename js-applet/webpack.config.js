const path = require("path");

module.exports = [
  {
    name: "base",
    mode: "production",
    entry: {
      base: ["./src/index.tsx"],
    },
    module: {
      rules: [
        {
          test: /\.(js|jsx)$/,
          exclude: /node_modules|dist/,
          use: {
            loader: "babel-loader",
            options: {
              presets: ["@babel/preset-react"],
            },
          },
        },
        {
          test: /\.(ts|tsx)$/,
          use: "ts-loader",
          exclude: /node_modules/,
        },
        {
          test: /\.css$/i,
          use: ["style-loader", "css-loader"],
        },
      ],
    },
    resolve: {
      extensions: [".tsx", ".ts", ".jsx", ".js"],
    },
    output: {
      path: path.resolve(__dirname, "dist"),
      publicPath: "",
      library: "NVLBase",
      libraryTarget: "var",
      clean: false,
    },
  },
];
